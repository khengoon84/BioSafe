
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

DEFAULT_CONSTITUTION_PATH = Path("/home/khengoon/biosafe/unified_v1/config/behavioral_constitution_v1_0.txt")

def load_constitution(path: str | Path = DEFAULT_CONSTITUTION_PATH) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Behavioral Constitution not found: {p}")
    return p.read_text(encoding="utf-8").strip()

def compose_system_prompt(base_system: str, constitution: str) -> str:
    base = (base_system or "").strip()
    c = (constitution or "").strip()
    marker = "=== BIOSAFE BEHAVIORAL CONSTITUTION v1.0 ==="
    if marker in base:
        return base
    return (
        base
        + "\n\n"
        + marker
        + "\n"
        + c
        + "\n=== END BIOSAFE BEHAVIORAL CONSTITUTION ==="
    ).strip()

def augment_compact_messages(
    messages: List[Dict[str, str]],
    *,
    constitution: str,
    interaction_context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """
    Preserve the retrieval-built user payload and original user query.
    Constitution is injected only in role=system.
    Interaction/case context is appended to the structured generation payload,
    never to the retrieval query.
    """
    if not messages:
        raise ValueError("Expected role-separated messages from BioSafe pipeline.")

    out = [dict(m) for m in messages]
    system_idx = next((i for i,m in enumerate(out) if m.get("role")=="system"), None)
    user_idx = next((i for i,m in enumerate(out) if m.get("role")=="user"), None)
    if system_idx is None or user_idx is None:
        raise ValueError("Expected both system and user messages.")

    out[system_idx]["content"] = compose_system_prompt(out[system_idx].get("content",""), constitution)

    ctx = interaction_context or {}
    try:
        payload = json.loads(out[user_idx].get("content") or "{}")
    except Exception as e:
        raise ValueError(f"Generation user payload is not valid JSON: {e}")

    # Important: user_query is left untouched.
    payload["interaction_context"] = {
        "intent": ctx.get("intent"),
        "case_state": ctx.get("case_state") or {},
        "resolved_reference": ctx.get("resolved_reference"),
        "conversation_summary": ctx.get("conversation_summary"),
        "attachments_present": bool(ctx.get("attachments_present")),
    }
    payload["behavior_contract"] = {
        "answer_current_question_first": True,
        "preserve_unknowns": True,
        "no_invented_regulatory_citations": True,
        "user_documents_are_scenario_evidence": True,
        "avoid_duplicate_sections": True,
        "hide_internal_metadata": True,
        "be_conversational_and_educational": True,
        "add_context_and_explanations": True,
    }
    out[user_idx]["content"] = json.dumps(payload, ensure_ascii=False, indent=2)
    return out

def assert_clean_query_preserved(before_messages, after_messages) -> bool:
    def q(messages):
        for m in messages:
            if m.get("role")=="user":
                try:
                    return json.loads(m["content"]).get("user_query")
                except Exception:
                    return None
        return None
    return q(before_messages) == q(after_messages)
