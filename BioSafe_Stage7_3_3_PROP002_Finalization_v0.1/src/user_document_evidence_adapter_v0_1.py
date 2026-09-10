
from __future__ import annotations
from typing import Any

def build_user_document_evidence(packet: dict[str, Any], max_items: int = 6) -> list[dict[str, Any]]:
    """
    Produce validator-friendly evidence objects for user-supplied documents.

    Namespace:
      DOC-<n>

    These are scenario/document evidence, not regulatory authority.
    """
    out = []
    idx = 1
    for doc in packet.get("structured_facts", []) or []:
        doc_id = doc.get("document_id")
        facts = doc.get("facts", []) or []
        seen = set()

        for fact in facts:
            span = fact.get("source_span")
            field = fact.get("field")
            if not span:
                continue
            key = (str(field), str(span).strip())
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "evidence_id": f"DOC-{idx}",
                "record_type": "user_document",
                "document_id": doc_id,
                "authority": "User-supplied document",
                "jurisdiction": doc.get("jurisdiction_hint") or "Unknown",
                "claim_type": "user_document_fact",
                "text": str(span),
                "source_field": field,
                "must_cite": False,
            })
            idx += 1
            if len(out) >= max_items:
                return out

        # Also expose normalized-profile fields as document evidence.
        profile = doc.get("normalized_profile") or {}
        for field in (
            "project_title", "principal_investigator", "institution",
            "project_duration", "proposed_start", "objectives",
            "facility", "waste", "transport", "emergency_response",
            "host_organism", "construct_identity", "culture_scale", "containment"
        ):
            value = profile.get(field)
            if value in (None, ""):
                continue
            key = (field, str(value).strip())
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "evidence_id": f"DOC-{idx}",
                "record_type": "user_document",
                "document_id": doc_id,
                "authority": "User-supplied document",
                "jurisdiction": doc.get("jurisdiction_hint") or "Unknown",
                "claim_type": "user_document_profile",
                "text": str(value),
                "source_field": field,
                "must_cite": False,
            })
            idx += 1
            if len(out) >= max_items:
                return out
    return out

def merge_document_evidence_into_bundle(
    bundle: dict[str, Any],
    packet: dict[str, Any],
    max_items: int = 6,
) -> dict[str, Any]:
    b = dict(bundle)
    existing = list(b.get("evidence_bundle", []) or [])
    doc_ev = build_user_document_evidence(packet, max_items=max_items)
    b["evidence_bundle"] = existing + doc_ev
    b["document_evidence_ids"] = [x["evidence_id"] for x in doc_ev]
    return b
