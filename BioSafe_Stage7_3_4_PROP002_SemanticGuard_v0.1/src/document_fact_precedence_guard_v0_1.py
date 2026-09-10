
from __future__ import annotations
import re
from typing import Any

def _all_document_text(packet: dict[str, Any]) -> str:
    vals = []
    for doc in packet.get("structured_facts", []) or []:
        for fact in doc.get("facts", []) or []:
            span = fact.get("source_span")
            if span:
                vals.append(str(span))
        profile = doc.get("normalized_profile") or {}
        for field in (
            "project_title", "objectives", "facility", "waste",
            "transport", "emergency_response"
        ):
            v = profile.get(field)
            if v:
                vals.append(str(v))
    return "\n".join(vals).lower()

def enforce_document_fact_precedence(
    output: dict[str, Any],
    packet: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(output, dict):
        return output, []

    doc_text = _all_document_text(packet)
    repaired = dict(output)
    changes = []

    # Explicit approved-courier statement takes precedence over generation.
    if "approved courier" in doc_text:
        def fix_text(s: str, field: str) -> str:
            original = s
            s = re.sub(
                r"\bunapproved courier\b",
                "approved courier (supporting approval evidence should be verified)",
                s,
                flags=re.I,
            )
            s = re.sub(
                r"\buse of an unapproved courier\b",
                "use of an approved courier whose supporting approval evidence should be verified",
                s,
                flags=re.I,
            )
            if s != original:
                changes.append(f"DOCUMENT_FACT_PRECEDENCE:{field}:approved_courier")
            return s

        repaired["conclusion"] = fix_text(str(repaired.get("conclusion") or ""), "conclusion")
        for field in ("missing_information", "recommended_next_step", "limitations"):
            vals = list(repaired.get(field) or [])
            if vals:
                repaired[field] = [fix_text(str(v), field) for v in vals]

    return repaired, list(dict.fromkeys(changes))
