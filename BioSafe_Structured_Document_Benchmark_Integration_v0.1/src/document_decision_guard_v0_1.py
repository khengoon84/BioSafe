
from __future__ import annotations

CERTIFICATION_PHRASES = [
    "is compliant",
    "complies with",
    "fully compliant",
    "approved",
    "meets all requirements",
    "adheres to all",
]

def apply_document_decision_guard(response: dict, packet: dict) -> tuple[dict, list[str]]:
    repairs = []
    conclusion = str(response.get("conclusion", ""))
    low = conclusion.lower()

    if any(p in low for p in CERTIFICATION_PHRASES):
        response["conclusion"] = (
            "The supplied document can be reviewed for apparent gaps and consistency, "
            "but BioSafe cannot certify compliance or official acceptability from the available information."
        )
        repairs.append("document_noncertification_shell")

    if packet.get("contradictions"):
        missing = response.setdefault("missing_information", [])
        if not any("contradiction" in str(x).lower() or "inconsisten" in str(x).lower() for x in missing):
            missing.append("Potential cross-document inconsistencies were detected and require human verification.")
            repairs.append("contradiction_visibility_shell")

    return response, repairs
