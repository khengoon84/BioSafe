
from __future__ import annotations
import re
from typing import Any

IBC_REPORT_PATTERNS = (
    r"\bsubmit\b.*\bibc assessment report\b",
    r"\bprovide\b.*\bibc assessment report\b",
    r"\bcomplete\b.*\bibc assessment report\b",
    r"\bprepare\b.*\bibc assessment report\b",
    r"\bresearcher\b.*\bibc assessment report\b",
    r"\bpi\b.*\bibc assessment report\b",
)

REPLACEMENT = (
    "Provide the researcher/PI information supported by the proposal and Form E. "
    "Any IBC Assessment Report or IBC-only determination remains the responsibility "
    "of the registered IBC and should not be treated as a researcher/PI field."
)

def enforce_researcher_ibc_boundary(output: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """
    Prevent researcher-facing recommendations from assigning IBC-only work to
    the researcher/PI. Does not remove evidence that explains the boundary.
    """
    if not isinstance(output, dict):
        return output, []

    repaired = dict(output)
    recs = list(repaired.get("recommended_next_step") or [])
    changes = []
    new_recs = []

    for rec in recs:
        s = str(rec)
        low = s.lower()
        if "ibc assessment report" in low and any(re.search(p, low) for p in IBC_REPORT_PATTERNS):
            new_recs.append(REPLACEMENT)
            changes.append("RESEARCHER_IBC_BOUNDARY: replaced researcher-facing IBC Assessment Report instruction")
        else:
            new_recs.append(rec)

    # Deduplicate if multiple bad recommendations were replaced.
    deduped = []
    for x in new_recs:
        if x not in deduped:
            deduped.append(x)
    repaired["recommended_next_step"] = deduped

    return repaired, changes
