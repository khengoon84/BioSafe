from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
VOCABULARY_PATH=HERE/"authorization_vocabulary_v0_1.json"

REQUIRED_VOCABULARY_KEYS=("high_stakes_terms","educational_terms","project_specific_markers","jurisdiction_terms","material_triggers","activity_verbs")


class AuthorizationIntent(str, Enum):
    EDUCATIONAL="EDUCATIONAL"
    AUTHORIZATION_APPLICABILITY="AUTHORIZATION_APPLICABILITY"
    COMPLIANCE_STATUS="COMPLIANCE_STATUS"
    START_WORK_READINESS="START_WORK_READINESS"
    CONTAINMENT_DETERMINATION="CONTAINMENT_DETERMINATION"
    CLASSIFICATION="CLASSIFICATION"
    NONE="NONE"


EVIDENCE_REQUIRED="REQUIRED"
EVIDENCE_OPTIONAL_EDUCATIONAL="OPTIONAL_EDUCATIONAL"
EVIDENCE_NOT_REQUIRED="NOT_REQUIRED"

CANONICAL_FACT_JURISDICTION="jurisdiction"
CANONICAL_FACT_TRIGGER="material_or_technology_trigger"
CANONICAL_FACT_ACTIVITY="specific_activity"


@dataclass(frozen=True)
class AuthorizationDecision:
    intent: AuthorizationIntent
    high_stakes: bool
    retrieval_required: bool
    positive_determination_allowed: bool
    negative_determination_allowed: bool
    missing_facts: tuple[str, ...]
    reason_codes: tuple[str, ...]
    evidence_requirement: str
    jurisdiction_required: bool


def load_vocabulary(path: Path=VOCABULARY_PATH) -> dict[str, Any]:
    payload=json.loads(path.read_text(encoding="utf-8"))
    missing=[key for key in REQUIRED_VOCABULARY_KEYS if key not in payload]
    if missing:
        raise ValueError(f"authorization vocabulary missing keys: {sorted(missing)}")
    return payload


_VOCABULARY_CACHE: dict[str, Any]={}


def _vocabulary() -> dict[str, Any]:
    if not _VOCABULARY_CACHE:
        _VOCABULARY_CACHE.update(load_vocabulary())
    return _VOCABULARY_CACHE


def _contains_any(text: str, terms: list[str]) -> bool:
    # Word-boundary matching keeps short tokens such as "who" or "lmo" from
    # matching inside unrelated words ("whole", "flamingo").
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)


def classify_intent(query: str, vocabulary: dict[str, Any] | None=None) -> AuthorizationIntent:
    vocabulary=vocabulary or _vocabulary()
    text=(query or "").lower()
    if not text.strip():
        return AuthorizationIntent.NONE
    high_stakes=_contains_any(text, vocabulary["high_stakes_terms"])
    educational=_contains_any(text, vocabulary["educational_terms"])
    project_specific=_contains_any(text, vocabulary["project_specific_markers"])
    if high_stakes and educational:
        # An educational framing is honored only for generic concept questions.
        # A jurisdiction, material trigger, or activity makes the question a
        # project/requirement-specific applicability lookup, not a definition.
        specificity=_contains_any(text, vocabulary["jurisdiction_terms"]) or _contains_any(text, vocabulary["material_triggers"]) or _contains_any(text, vocabulary["activity_verbs"])
        if not project_specific and not specificity:
            return AuthorizationIntent.EDUCATIONAL
    if high_stakes:
        if "legal" in text or "compliant" in text or "compliance" in text:
            return AuthorizationIntent.COMPLIANCE_STATUS
        if "can i start" in text or "start work" in text or "begin work" in text:
            return AuthorizationIntent.START_WORK_READINESS
        return AuthorizationIntent.AUTHORIZATION_APPLICABILITY
    return AuthorizationIntent.EDUCATIONAL if educational else AuthorizationIntent.NONE


def extract_missing_facts(query: str, vocabulary: dict[str, Any] | None=None) -> tuple[str, ...]:
    vocabulary=vocabulary or _vocabulary()
    text=(query or "").lower()
    missing: list[str]=[]
    if not _contains_any(text, vocabulary["jurisdiction_terms"]):
        missing.append(CANONICAL_FACT_JURISDICTION)
    if not _contains_any(text, vocabulary["material_triggers"]):
        missing.append(CANONICAL_FACT_TRIGGER)
    if not _contains_any(text, vocabulary["activity_verbs"]):
        missing.append(CANONICAL_FACT_ACTIVITY)
    return tuple(missing)


def evaluate_authorization_decision(query: str, vocabulary: dict[str, Any] | None=None) -> AuthorizationDecision:
    """Deterministic, fail-closed authorization decision for a user query.

    No model inference and no regex beyond vocabulary substring checks. When a
    query is high-stakes and required project facts are missing, positive and
    negative determinations are both forbidden.
    """
    vocabulary=vocabulary or _vocabulary()
    intent=classify_intent(query, vocabulary)
    text=(query or "").lower()
    high_stakes=intent is not AuthorizationIntent.EDUCATIONAL and intent is not AuthorizationIntent.NONE
    missing_facts: tuple[str, ...]=()
    reason_codes: list[str]=[]
    if intent is AuthorizationIntent.EDUCATIONAL:
        reason_codes=["EDUCATIONAL_QUERY","NO_AUTHORIZATION_DETERMINATION"]
    elif intent is AuthorizationIntent.NONE:
        reason_codes=["NO_AUTHORIZATION_INTENT"]
    else:
        reason_codes=["HIGH_STAKES_AUTHORIZATION_QUERY"]
        missing_facts=extract_missing_facts(text, vocabulary)
        if missing_facts:
            reason_codes.append("INSUFFICIENT_FACTS")
        else:
            reason_codes.append("EVIDENCE_REVIEW_REQUIRED")
    if intent is AuthorizationIntent.EDUCATIONAL:
        evidence_requirement=EVIDENCE_OPTIONAL_EDUCATIONAL
    elif high_stakes:
        evidence_requirement=EVIDENCE_REQUIRED
    else:
        evidence_requirement=EVIDENCE_NOT_REQUIRED
    facts_complete=high_stakes and not missing_facts
    return AuthorizationDecision(
        intent=intent,
        high_stakes=high_stakes,
        retrieval_required=high_stakes,
        positive_determination_allowed=facts_complete,
        negative_determination_allowed=facts_complete,
        missing_facts=missing_facts,
        reason_codes=tuple(reason_codes),
        evidence_requirement=evidence_requirement,
        jurisdiction_required=high_stakes,
    )


def decision_summary(decision: AuthorizationDecision) -> dict[str, Any]:
    """JSON-serializable audit view of a decision; safe to embed in _meta."""
    return {
        "intent": decision.intent.value,
        "high_stakes": decision.high_stakes,
        "retrieval_required": decision.retrieval_required,
        "positive_determination_allowed": decision.positive_determination_allowed,
        "negative_determination_allowed": decision.negative_determination_allowed,
        "missing_facts": list(decision.missing_facts),
        "reason_codes": list(decision.reason_codes),
        "evidence_requirement": decision.evidence_requirement,
        "jurisdiction_required": decision.jurisdiction_required,
    }
