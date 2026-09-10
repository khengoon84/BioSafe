
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
    return "\n".join(vals).lower()

def enforce_document_fact_precedence(
    output: dict[str, Any],
    packet: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(output, dict):
        return output, []

    doc_text = _all_document_text(packet)
    if "approved courier" not in doc_text:
        return output, []

    repaired = dict(output)
    changes = []

    conclusion = str(repaired.get("conclusion") or "")
    if re.search(r"\bunapproved courier\b", conclusion, flags=re.I):
        repaired["conclusion"] = re.sub(
            r"\bunapproved courier\b",
            "courier approval status requiring verification",
            conclusion,
            flags=re.I,
        )
        changes.append("DOCUMENT_FACT_PRECEDENCE: corrected contradiction with explicit approved-courier statement")

    for field in ("missing_information", "recommended_next_step", "limitations"):
        vals = list(repaired.get(field) or [])
        if not vals:
            continue
        new_vals = []
        for v in vals:
            s = str(v)
            if re.search(r"\bunapproved courier\b", s, flags=re.I):
                s = re.sub(
                    r"\bunapproved courier\b",
                    "courier approval status requiring verification",
                    s,
                    flags=re.I,
                )
                changes.append(f"DOCUMENT_FACT_PRECEDENCE:{field}")
            new_vals.append(s)
        repaired[field] = new_vals

    return repaired, list(dict.fromkeys(changes))
