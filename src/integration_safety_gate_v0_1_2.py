
from __future__ import annotations
import re
from integration_safety_gate_v0_1 import classify_safety as _base_classify_safety, SafetyDecision

_HARMFUL_CAPABILITY_PATTERNS = [
    re.compile(r"\bincrease(?:s|d|ing)?\b.{0,60}\bharmful\b.{0,30}\bbiological\b.{0,30}\bcapabilit", re.I),
    re.compile(r"\benhance(?:s|d|ing)?\b.{0,60}\bharmful\b.{0,30}\bbiological\b.{0,30}\bcapabilit", re.I),
    re.compile(r"\bmake\b.{0,40}\b(?:organism|pathogen|agent)\b.{0,60}\bmore harmful\b", re.I),
    re.compile(r"\bactionable\b.{0,80}\b(?:increase|enhance)\b.{0,60}\b(?:harm|virulence|pathogenicity|biological capability)\b", re.I),
]

_ACTIONABLE_HARMFUL_MODIFICATION_PATTERNS = [
    re.compile(r"\bsteps?\b.{0,50}\b(?:increase|enhance)\b.{0,60}\b(?:virulence|pathogenicity|harmful capability)\b", re.I),
    re.compile(r"\binstructions?\b.{0,50}\b(?:increase|enhance)\b.{0,60}\b(?:virulence|pathogenicity|harmful capability)\b", re.I),
]

def _decision(restricted: bool, reason: str = "", matched: list[str] | None = None) -> SafetyDecision:
    return SafetyDecision(restricted, reason, matched or [])

def classify_safety(query: str) -> SafetyDecision:
    """
    v0.1.2 preserves the original v0.1 decision first, then adds only the
    missing deterministic harmful-capability coverage.
    """
    base = _base_classify_safety(query)
    if getattr(base, "restricted", False):
        return base

    q = query or ""

    for pat in _HARMFUL_CAPABILITY_PATTERNS:
        if pat.search(q):
            return _decision(
                True,
                "Request may enable harmful biological capability or defeat containment.",
                ["increase harmful biological capability"],
            )

    for pat in _ACTIONABLE_HARMFUL_MODIFICATION_PATTERNS:
        if pat.search(q):
            return _decision(
                True,
                "Request may enable actionable harmful biological modification.",
                ["actionable harmful modification"],
            )

    return base
