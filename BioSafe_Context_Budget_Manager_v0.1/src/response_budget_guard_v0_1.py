
from __future__ import annotations
from typing import Any

def enforce_response_budget(
    output: dict[str, Any],
    max_missing: int,
    max_recommendations: int,
    max_limitations: int,
    max_evidence: int,
):
    if not isinstance(output, dict):
        return output, []

    repaired = dict(output)
    changes = []
    for field, limit in {
        "evidence": max_evidence,
        "missing_information": max_missing,
        "recommended_next_step": max_recommendations,
        "limitations": max_limitations,
    }.items():
        vals = list(repaired.get(field) or [])
        if len(vals) > limit:
            repaired[field] = vals[:limit]
            changes.append(f"RESPONSE_BUDGET:{field}:{len(vals)}->{limit}")

    words = str(repaired.get("conclusion") or "").split()
    if len(words) > 90:
        repaired["conclusion"] = " ".join(words[:90]).rstrip(" ,;:") + "."
        changes.append(f"RESPONSE_BUDGET:conclusion:{len(words)}->90_words")

    return repaired, changes
