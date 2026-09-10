
from __future__ import annotations
import re
from typing import Any

def enforce_clinical_proposal_semantic_guard(
    output: dict[str, Any],
    packet: dict[str, Any],
    evidence_bundle: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """
    Final narrow guard for clinical-specimen proposal review.

    Prevents:
    - treating Category A/B as already established;
    - inventing a required 'risk assessment matrix';
    - unsupported 'formal regulatory approval' recommendations;
    - overstating documentation gaps as confirmed non-compliance.
    """
    if not isinstance(output, dict):
        return output, []

    doc_types = {
        d.get("document_type")
        for d in (packet.get("structured_facts", []) or [])
    }
    if "clinical_specimen_proposal" not in doc_types:
        return output, []

    repaired = dict(output)
    changes = []

    def fix_text(s: str, field: str) -> str:
        original = s

        s = re.sub(
            r"if not properly classified as Category A/B",
            "until the applicable specimen/infectious-substance classification is confirmed",
            s,
            flags=re.I,
        )
        s = re.sub(
            r"classified as Category A/B",
            "classified according to the applicable transport requirements",
            s,
            flags=re.I,
        )
        s = re.sub(
            r"\brisk assessment (?:matrix|matrices)\b",
            "activity-specific risk assessment",
            s,
            flags=re.I,
        )
        s = re.sub(
            r"\b(?:creating|creates?) a gap in regulatory compliance\b",
            "creating a documentation gap that requires clarification",
            s,
            flags=re.I,
        )
        s = re.sub(
            r"\bcritical biosafety weaknesses\b",
            "important biosafety documentation gaps",
            s,
            flags=re.I,
        )

        if s != original:
            changes.append(f"CLINICAL_PROPOSAL_SEMANTIC_GUARD:{field}")
        return s

    repaired["conclusion"] = fix_text(str(repaired.get("conclusion") or ""), "conclusion")

    for field in ("missing_information", "limitations"):
        vals = list(repaired.get(field) or [])
        if vals:
            repaired[field] = [fix_text(str(v), field) for v in vals]

    recs = []
    for rec in list(repaired.get("recommended_next_step") or []):
        s = fix_text(str(rec), "recommended_next_step")
        if re.search(r"obtain formal regulatory approval.*transport classification", s, flags=re.I):
            s = (
                "Confirm the applicable specimen classification, transport requirements, "
                "and waste-management requirements using the relevant Malaysian guidance "
                "and institutional procedures before finalising the proposal."
            )
            changes.append("CLINICAL_PROPOSAL_SEMANTIC_GUARD:unsupported_formal_approval")
        recs.append(s)

    if recs:
        repaired["recommended_next_step"] = recs

    return repaired, list(dict.fromkeys(changes))
