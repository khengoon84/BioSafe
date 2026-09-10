from __future__ import annotations
import re
from typing import Iterable

ABSENCE_OR_UNCERTAINTY_PATTERNS = [
    r"\bnot\s+(?:fully\s+)?described\b",
    r"\bnot\s+specified\b",
    r"\bnot\s+provided\b",
    r"\bnot\s+described\b",
    r"\bnot\s+known\b",
    r"\bunknown\b",
    r"\bto\s+be\s+confirmed\b",
    r"\bwill\s+be\s+determined\b",
    r"\bwill\s+be\s+confirmed\b",
    r"\bdepends?\s+on\b",
]


def _sentence_spans(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _is_unclear_or_absent(span: str) -> bool:
    return any(re.search(p, span, flags=re.I) for p in ABSENCE_OR_UNCERTAINTY_PATTERNS)


def extract_rule_based_facts(text: str, rules: Iterable[dict]) -> list[dict]:
    spans = _sentence_spans(text)
    out = []
    for rule in rules:
        hits = []
        for span in spans:
            low = span.lower()
            if any(p.lower() in low for p in rule.get("patterns", [])):
                hits.append(span)
        if hits:
            # Prefer an explicit positive statement if one exists. Otherwise preserve
            # the uncertainty as an 'unclear' fact so missing-field detection can act.
            positive = next((h for h in hits if not _is_unclear_or_absent(h)), None)
            chosen = positive or hits[0]
            status = "present" if positive else "unclear"
            out.append({
                "field": rule["field"],
                "value": chosen,
                "status": status,
                "source_span": chosen,
                "confidence": 0.8 if status == "present" else 0.9,
            })
    return out


def find_vague_statements(text: str, vague_terms: list[str]) -> list[str]:
    low = text.lower()
    found = []
    for term in vague_terms:
        if term.lower() in low:
            found.append(term)
    return found
