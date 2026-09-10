
from __future__ import annotations
import json
from typing import Any

CLINICAL_QUERY_TERMS = (
    "clinical specimen", "clinical sample", "infectious substance",
    "category a", "category b", "p620", "p650",
)

TRANSPORT_QUERY_TERMS = (
    "transport", "shipping", "courier", "road", "air transport",
    "packaging", "transfer outside",
)

LMO_DOC_TYPES = {"lmo_gmm_sop", "lmo_gmm_proposal", "form_e_completed", "form_e_structure"}

LMO_PREFERRED_DOCS = {
    "KB-MY-ACT678",
    "KB-MY-REG2010",
    "KB-MY-CU",
    "KB-MY-GMMRA",
    "KB-MY-FORME",
    "KB-MY-IBC",
    "KB-WHO-RA",
    "KB-WHO-LBM4",
    "KB-WHO-PPE",
}

def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    t = (text or "").lower()
    return any(term in t for term in terms)

def filter_document_review_evidence(
    query: str,
    document_types: list[str],
    evidence_bundle: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Context-level relevance filter. It does NOT alter CFG-02 retrieval scores.

    Purpose:
    - prevent clinical-specimen transport claims from dominating an LMO/GMM
      document review when the user did not ask a transport/clinical question;
    - retain the original retrieved IDs in an audit record.
    """
    doc_types = set(document_types)
    is_lmo_review = bool(doc_types & LMO_DOC_TYPES)
    clinical_intent = _contains_any(query, CLINICAL_QUERY_TERMS)
    transport_intent = _contains_any(query, TRANSPORT_QUERY_TERMS)

    kept = []
    suppressed = []

    for ev in evidence_bundle or []:
        doc_id = ev.get("document_id")
        claim_type = str(ev.get("claim_type") or "").lower()
        title = str(ev.get("title") or "").lower()

        suppress = False

        if is_lmo_review and not clinical_intent and not transport_intent:
            # The MOH 2023 source is specifically clinical-specimen /
            # infectious-substance transport guidance. It should not dominate
            # a generic LMO/GMM SOP or proposal review.
            if doc_id == "KB-MY-MOH2023":
                suppress = True
            elif claim_type in {"transport", "transport_scope"} and "clinical" in title:
                suppress = True

        if suppress:
            suppressed.append(ev)
        else:
            kept.append(ev)

    # Avoid accidental zero-evidence prompts. If filtering removes everything,
    # keep the best original claim and mark that the filter was conservative.
    fallback_used = False
    if evidence_bundle and not kept:
        kept = [evidence_bundle[0]]
        suppressed = [x for x in evidence_bundle[1:]]
        fallback_used = True

    audit = {
        "mode": "DOCUMENT_CONTEXT_EVIDENCE_FILTER",
        "is_lmo_review": is_lmo_review,
        "clinical_intent": clinical_intent,
        "transport_intent": transport_intent,
        "original_evidence_ids": [x.get("evidence_id") for x in evidence_bundle or []],
        "exposed_evidence_ids": [x.get("evidence_id") for x in kept],
        "suppressed_evidence_ids": [x.get("evidence_id") for x in suppressed],
        "fallback_used": fallback_used,
        "note": "CFG-02 ranking is unchanged; this controls only what document-review evidence is exposed to the model.",
    }
    return kept, audit

def patch_message_evidence(messages: list[dict], filtered_evidence: list[dict]) -> list[dict]:
    """Replace only evidence_bundle in the existing user payload."""
    out = [dict(m) for m in messages]
    for i, m in enumerate(out):
        if m.get("role") != "user":
            continue
        try:
            payload = json.loads(m.get("content") or "")
        except Exception:
            continue
        if isinstance(payload, dict) and "evidence_bundle" in payload:
            payload["evidence_bundle"] = filtered_evidence
            out[i]["content"] = json.dumps(payload, ensure_ascii=False, indent=2)
            break
    return out
