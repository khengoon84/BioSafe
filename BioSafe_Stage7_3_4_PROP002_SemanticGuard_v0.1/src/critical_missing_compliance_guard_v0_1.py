
from __future__ import annotations
import re
from typing import Any

RISKY_ALIGNMENT_PATTERNS = (
    r"\bappears?\s+(?:to\s+be\s+)?aligned\b",
    r"\baligned\s+with\s+(?:biosafety|regulatory|legal)\b",
    r"\bappears?\s+(?:to\s+be\s+)?compliant\b",
    r"\bmeets?\s+(?:biosafety|regulatory|legal)\s+requirements\b",
)

SAFE_CONCLUSION = (
    "I cannot determine or certify biosafety compliance or approval from the supplied information. "
    "The document contains material information gaps that must be resolved before a defensible assessment can be made."
)

def enforce_critical_missing_compliance_boundary(
    output: dict[str, Any],
    policy_decision: dict[str, Any],
    packet: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(output, dict):
        return output, []

    mode = (policy_decision or {}).get("mode")
    if mode != "ASSESS_NOT_CERTIFY":
        return output, []

    critical_missing = []
    for m in packet.get("missing_information", []) or []:
        if str(m.get("severity", "")).lower() == "critical":
            critical_missing.append(m)

    if not critical_missing:
        return output, []

    repaired = dict(output)
    conclusion = str(repaired.get("conclusion") or "")
    low = conclusion.lower()

    if any(re.search(p, low) for p in RISKY_ALIGNMENT_PATTERNS):
        repaired["conclusion"] = SAFE_CONCLUSION
        return repaired, [
            "CRITICAL_MISSING_COMPLIANCE_BOUNDARY: replaced over-permissive alignment/compliance conclusion"
        ]

    return repaired, []
