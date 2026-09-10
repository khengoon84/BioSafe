
from __future__ import annotations
from typing import Any

def _authority_list(evidence_bundle: list[dict[str, Any]], max_items: int = 2) -> list[str]:
    out = []
    for ev in evidence_bundle or []:
        if ev.get("record_type") == "user_document":
            continue
        authority = str(ev.get("authority") or "").strip()
        if authority and authority not in out:
            out.append(authority)
        if len(out) >= max_items:
            break
    return out

def _canonical_evidence(evidence_bundle: list[dict[str, Any]], max_items: int = 3) -> list[dict[str, str]]:
    out = []
    # Prefer regulatory RAG, then substantive DOC evidence in frozen order.
    for ev in evidence_bundle or []:
        eid = ev.get("evidence_id")
        text = ev.get("text")
        if not eid or not text:
            continue
        out.append({"evidence_id": str(eid), "statement": str(text)})
        if len(out) >= max_items:
            break
    return out

def _safety_from_bundle(bundle: dict[str, Any]) -> dict[str, str]:
    pd = bundle.get("policy_decision") or {}
    mode = str(pd.get("mode") or "")
    # Document review is normally cautionary unless an upstream hard safety
    # gate has already short-circuited.
    if mode in {"ASK_BEFORE_SAFETY_CONCLUSION", "ASK_BEFORE_TRANSPORT_CONCLUSION"}:
        return {
            "classification": "caution",
            "response_mode": "ask_before_concluding",
            "reason": "Additional scenario information is required before a defensible conclusion."
        }
    return {
        "classification": "caution",
        "response_mode": "answer",
        "reason": "Document review is advisory and does not certify compliance or approval."
    }

def assemble_biosafe_response(
    compact_model_output: dict[str, Any],
    bundle: dict[str, Any],
    *,
    max_missing: int = 3,
    max_recommendations: int = 2,
    max_evidence: int = 3,
    max_limitations: int = 1,
) -> dict[str, Any]:
    """
    Qwen supplies only reasoning-bearing fields. BioSafe deterministically
    assembles authority, canonical evidence, limitations and safety.
    """
    model = compact_model_output if isinstance(compact_model_output, dict) else {}

    conclusion = str(model.get("conclusion") or "").strip()
    missing = [str(x) for x in (model.get("missing_information") or []) if str(x).strip()]
    recs = [str(x) for x in (model.get("recommended_next_step") or []) if str(x).strip()]

    limitations = []
    if conclusion or missing or recs:
        limitations = [
            "BioSafe provides an evidence-based advisory review and does not certify regulatory compliance or approval."
        ][:max_limitations]

    return {
        "conclusion": conclusion,
        "applicable_authority": _authority_list(bundle.get("evidence_bundle", []), 2),
        "evidence": _canonical_evidence(bundle.get("evidence_bundle", []), max_evidence),
        "missing_information": missing[:max_missing],
        "recommended_next_step": recs[:max_recommendations],
        "limitations": limitations,
        "safety": _safety_from_bundle(bundle),
    }
