
from __future__ import annotations
from typing import Any

MAX_CONFLICTS = 7

def compact_conflict_findings(packet: dict[str, Any]) -> list[str]:
    findings = []
    for c in (packet.get("contradictions") or [])[:MAX_CONFLICTS]:
        field = c.get("field") or "unspecified_field"
        kind = c.get("finding_type") or c.get("status") or "possible_conflict"
        a = c.get("value_a")
        b = c.get("value_b")

        if kind == "unsupported_secondary_detail":
            findings.append(
                f"{field}: the secondary document supplies a specific value "
                f"({b!r}) while the primary document does not support that detail."
            )
        elif a is not None and b is not None:
            findings.append(
                f"{field}: primary document states {a!r}; secondary document states {b!r}."
            )
        else:
            findings.append(f"{field}: {kind}.")
    return findings

def build_compact_contradiction_fallback(
    packet: dict[str, Any],
    evidence_bundle: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Deterministic fallback used only when the model output is invalid/truncated
    AND structured cross-document conflicts already exist.
    """
    findings = compact_conflict_findings(packet)
    evidence = []
    for ev in (evidence_bundle or [])[:3]:
        evidence.append({
            "evidence_id": ev.get("evidence_id"),
            "statement": ev.get("text") or "",
        })

    return {
        "conclusion": (
            "Potential inconsistencies were identified between the supplied documents. "
            "They should be verified rather than silently reconciled."
        ),
        "applicable_authority": list(dict.fromkeys(
            [x.get("authority") for x in (evidence_bundle or []) if x.get("authority")]
        ))[:3],
        "evidence": evidence,
        "missing_information": findings or [
            "A complete consistency determination cannot be made from the available structured comparison."
        ],
        "recommended_next_step": [
            "Verify each listed conflicting field against the source proposal and completed Form E.",
            "Correct the documents so the project details are internally consistent before further regulatory review.",
        ],
        "limitations": [
            "The conflict findings are derived from user-supplied documents and are not regulatory determinations.",
            "BioSafe does not certify compliance, approval, or IBC acceptance.",
        ],
        "safety": {
            "classification": "normal",
            "response_mode": "ask_before_concluding",
            "reason": "Cross-document discrepancies require verification."
        },
    }
