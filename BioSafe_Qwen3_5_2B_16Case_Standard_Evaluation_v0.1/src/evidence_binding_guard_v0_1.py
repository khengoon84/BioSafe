
from __future__ import annotations
import re
from typing import Any

def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())

def enforce_evidence_binding(
    output: dict[str, Any],
    evidence_bundle: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """
    Final evidence integrity guard:
    - evidence_id determines canonical statement text;
    - authorities are grounded to retrieved non-user authority names;
    - duplicate wording introduced by prior deterministic repairs is cleaned.
    """
    if not isinstance(output, dict):
        return output, []

    repaired = dict(output)
    changes = []
    registry = {
        str(ev.get("evidence_id")): ev
        for ev in (evidence_bundle or [])
        if ev.get("evidence_id")
    }

    # Canonicalize evidence statements to the registered evidence text.
    new_evidence = []
    for item in list(repaired.get("evidence") or []):
        if not isinstance(item, dict):
            new_evidence.append(item)
            continue
        item2 = dict(item)
        eid = str(item2.get("evidence_id") or "")
        ev = registry.get(eid)
        if ev is not None:
            canonical = str(ev.get("text") or "")
            if canonical and _norm(str(item2.get("statement") or "")) != _norm(canonical):
                item2["statement"] = canonical
                changes.append(f"EVIDENCE_BINDING:{eid}:statement_canonicalized")
        new_evidence.append(item2)
    repaired["evidence"] = new_evidence

    # Ground applicable authorities to non-user retrieved evidence only.
    canonical_authorities = []
    for ev in evidence_bundle or []:
        if ev.get("record_type") == "user_document":
            continue
        authority = ev.get("authority")
        if authority and authority not in canonical_authorities:
            canonical_authorities.append(authority)

    if canonical_authorities:
        current = list(repaired.get("applicable_authority") or [])
        if current != canonical_authorities[:3]:
            repaired["applicable_authority"] = canonical_authorities[:3]
            changes.append("EVIDENCE_BINDING:authority_grounded")

    # Clean duplicated repair wording.
    def clean(s: str, field: str) -> str:
        original = s
        s = re.sub(
            r"\bactivity-specific\s+activity-specific\b",
            "activity-specific",
            s,
            flags=re.I,
        )
        if s != original:
            changes.append(f"EVIDENCE_BINDING:{field}:duplicate_wording_cleaned")
        return s

    repaired["conclusion"] = clean(str(repaired.get("conclusion") or ""), "conclusion")
    for field in ("missing_information", "recommended_next_step", "limitations"):
        vals = list(repaired.get(field) or [])
        if vals:
            repaired[field] = [clean(str(v), field) for v in vals]

    return repaired, list(dict.fromkeys(changes))
