
from __future__ import annotations

def detect_missing_fields(facts: list[dict], rules: list[dict]) -> list[dict]:
    present = {f["field"] for f in facts if f.get("status") == "present"}
    missing = []
    for rule in rules:
        if rule["field"] not in present:
            missing.append({
                "field": rule["field"],
                "reason": "Required review field was not found explicitly in the supplied document.",
                "severity": rule.get("severity", "medium")
            })
    return missing
