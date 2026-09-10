
from __future__ import annotations
from typing import Any

PLACEHOLDER = "[Information not provided — confirmation required]"
FIELDS = (
    "project_title", "principal_investigator", "institution",
    "project_duration", "proposed_start", "objectives",
    "host_organism", "construct_identity", "facility",
    "culture_scale", "containment", "waste", "transport",
    "emergency_response",
)

def _primary_profile(packet: dict[str, Any]) -> dict[str, Any]:
    docs = packet.get("structured_facts", []) or []
    for doc in docs:
        if doc.get("document_type") in {"lmo_gmm_proposal", "clinical_specimen_proposal", "research_proposal"}:
            return doc.get("normalized_profile") or {}
    return (docs[0].get("normalized_profile") or {}) if docs else {}

def _label(field: str) -> str:
    return field.replace("_", " ").title()

def build_source_only_draft_response(
    packet: dict[str, Any],
    evidence_bundle: list[dict[str, Any]],
) -> dict[str, Any]:
    profile = _primary_profile(packet)
    statuses = profile.get("_status") or {}

    missing = []
    for field in FIELDS:
        value = profile.get(field)
        status = statuses.get(field, "missing")
        if value in (None, "") or status != "present":
            missing.append(f"{_label(field)}: {PLACEHOLDER}")

    evidence = []
    for ev in evidence_bundle or []:
        if len(evidence) >= 3:
            break
        if ev.get("record_type") == "user_document" or ev.get("must_cite"):
            evidence.append({
                "evidence_id": ev.get("evidence_id"),
                "statement": ev.get("text") or "",
            })

    authorities = []
    for ev in evidence_bundle or []:
        if ev.get("record_type") == "user_document":
            continue
        auth = ev.get("authority")
        if auth and auth not in authorities:
            authorities.append(auth)

    return {
        "conclusion": (
            "The supported fields can be drafted from the supplied proposal, "
            "but the listed missing fields require confirmation."
        ),
        "applicable_authority": authorities[:3],
        "evidence": evidence,
        "missing_information": missing[:8],
        "recommended_next_step": [
            "Transfer only information directly supported by the supplied proposal.",
            f"Use {PLACEHOLDER} for fields not supported by the proposal.",
            "Confirm the listed missing fields before submission."
        ],
        "limitations": [
            "This source-only draft does not certify completeness, compliance or approval.",
            "User-supplied documents are scenario evidence, not regulatory authority."
        ],
        "safety": {
            "classification": "normal",
            "response_mode": "ask_before_concluding",
            "reason": "Required Form E fields remain unsupported by the supplied proposal."
        }
    }
