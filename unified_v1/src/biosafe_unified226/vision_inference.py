"""
Vision-capable inference for image uploads (non-frozen layer).

qwen3.5:0.8b and qwen3.5:2b report the 'vision' capability via the local Ollama
instance, but the frozen inference core only consumes text documents. This
module short-circuits image uploads: it builds an Ollama /api/chat message with
an `images` array (raw base64) and a focused biosafety observation prompt, calls
the vision-capable model, and returns a compact response dict that the existing
non-frozen guards then vet.

Frozen inference code is untouched; fall-through for text documents is unchanged.

Safety contract:
- The prompt asks for biosafety observations, hazard/containment style, and
  document-vs-photo classification - never for steps to bypass containment or
  to produce, weaponize, or release harmful agents.
- Model output is untrusted text and still passes through the existing
  DecisionSemanticsGuard / SafetyRationaleGuard / RequestedSubjectCoverageGuard
  before being returned.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List, Optional

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
VISION_MODEL = "qwen3.5:2b"
VISION_OUTPUT_BUDGET = 520
MAX_IMAGE_BASE64_CHARS = 20_000_000

VISION_SYSTEM_PROMPT = (
    "You are BioSafe, an evidence-grounded biosafety and biosecurity assistant. "
    "You are looking at a photograph or image uploaded by a user. "
    "Describe what is depicted and give constructive biosafety-relevant observations "
    "(e.g., possible hazards visible, apparent containment style, PPE, labelling, "
    "housekeeping, or whether the image appears to be a document/screenshot). "
    "Be honest about uncertainty - if the image content is unclear, say so. "
    "Never claim regulatory compliance or approval. "
    "Never provide instructions that increase harmful biological capability or bypass "
    "containment. Reply in plain prose; keep it concise and educational."
)

VISION_USER_TEMPLATE = (
    "A user uploaded the image(s) labelled below and asked: \"{query}\"\n\n"
    "Images:\n{image_labels}\n\n"
    "Please provide your biosafety-relevant observations of what the image shows."
)


def is_image_document(doc: Dict[str, Any]) -> bool:
    """True when a document carries an image payload (data URL or raw base64)."""
    if not isinstance(doc, dict):
        return False
    if doc.get("is_image"):
        return True
    image = doc.get("image")
    if isinstance(image, str) and image.strip():
        return True
    return False


def _as_base64(image: str) -> str:
    """Normalize an image value into raw base64 for Ollama's ``images`` field."""
    img = (image or "").strip()
    if img.startswith("data:"):
        marker = ";base64,"
        if marker not in img:
            raise ValueError("Image data URL is not base64 encoded.")
        img = img.split(marker, 1)[1]
    if len(img) > MAX_IMAGE_BASE64_CHARS:
        raise ValueError("Image exceeds the local vision payload limit.")
    return img


def build_vision_messages(
    query: str,
    images: List[str],
    constitution: Optional[str] = None,
) -> List[Dict[str, Any]]:
    labels = "\n".join(
        f"- Image {i + 1}: <uploaded image>" for i in range(len(images))
    )
    user_content = VISION_USER_TEMPLATE.format(query=query, image_labels=labels)
    messages: List[Dict[str, Any]] = []
    if constitution:
        messages.append(
            {"role": "system", "content": VISION_SYSTEM_PROMPT + "\n\n" + constitution}
        )
    else:
        messages.append({"role": "system", "content": VISION_SYSTEM_PROMPT})
    messages.append(
        {
            "role": "user",
            "content": user_content,
            "images": [_as_base64(img) for img in images],
        }
    )
    return messages


def call_ollama_vision(
    model: str,
    messages: List[Dict[str, Any]],
    num_predict: int = VISION_OUTPUT_BUDGET,
    timeout: int = 900,
) -> Dict[str, Any]:
    """POST messages (with images) to the local Ollama chat endpoint."""
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_predict": int(num_predict)},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return payload
def run_vision_inference(
    query: str,
    documents: List[Dict[str, Any]],
    constitution: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Short-circuit path for image uploads. Returns a BioSafe-shaped response dict
    with the model's observations in `conclusion`.

    If the Ollama endpoint is unreachable, returns an explicit, honest fallback
    rather than mislabelling the image as a text document.
    """
    images = [
        d.get("image", "") for d in (documents or []) if is_image_document(d)
    ]
    if not images:
        return {
            "conclusion": "No viewable image payload was received, so no visual analysis is possible.",
            "applicable_authority": [],
            "evidence": [],
            "missing_information": [],
            "recommended_next_step": [
                "Upload a clear image file (PNG/JPEG) or describe the photo in text."
            ],
            "limitations": [],
            "safety": {
                "classification": "normal",
                "response_mode": "answer",
                "reason": "No image data received; no visual claim made.",
            },
        }

    try:
        messages = build_vision_messages(query, images, constitution)
        payload = call_ollama_vision(VISION_MODEL, messages)
    except Exception as exc:  # network / ollama down / model error
        return {
            "conclusion": (
                "I received an image, but the local vision model could not be reached "
                "to analyse it. This is a service availability issue, not a problem "
                "with your image."
            ),
            "applicable_authority": [],
            "evidence": [],
            "missing_information": [],
            "recommended_next_step": [
                "Retry in a moment, or describe the image contents in text so I can still help."
            ],
            "limitations": [f"Image analysis unavailable: {type(exc).__name__}"],
            "safety": {
                "classification": "normal",
                "response_mode": "answer",
                "reason": "Vision inference unavailable; no visual claim made.",
            },
        }

    raw = ((payload.get("message") or {}).get("content") or "").strip()
    if not raw:
        raw = "The image was received, but the vision model returned an empty response."
    return {
        "conclusion": raw,
        "applicable_authority": [],
        "evidence": [],
        "missing_information": [],
        "recommended_next_step": [],
        "limitations": [
            "Image observation is advisory and does not certify compliance or approval."
        ],
        "safety": {
            "classification": "normal",
            "response_mode": "answer",
            "reason": "Educational image observation from the vision-capable model.",
        },
        "_meta": {"route": "vision_inference", "model": VISION_MODEL, "model_called": True},
    }