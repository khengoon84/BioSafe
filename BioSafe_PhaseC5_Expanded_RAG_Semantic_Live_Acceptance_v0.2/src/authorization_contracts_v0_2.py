from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class FactStatus(str, Enum):
    UNKNOWN="UNKNOWN"
    USER_ASSERTED="USER_ASSERTED"
    EXTRACTED_UNVERIFIED="EXTRACTED_UNVERIFIED"
    VERIFIED="VERIFIED"
    CONFLICTING="CONFLICTING"


@dataclass(frozen=True)
class AuthorizationFact:
    name: str
    value: Any = None
    status: FactStatus = FactStatus.UNKNOWN
    source: str | None = None


class AuthorizationClaimKind(str, Enum):
    AUTHORIZATION_REQUIREMENT="AUTHORIZATION_REQUIREMENT"
    UNKNOWN_REGULATORY_REQUIREMENT="UNKNOWN_REGULATORY_REQUIREMENT"


class AuthorizationPolarity(str, Enum):
    REQUIRED="REQUIRED"
    NOT_REQUIRED="NOT_REQUIRED"


@dataclass(frozen=True)
class AuthorizationClaimCandidate:
    kind: AuthorizationClaimKind
    concept: str | None
    polarity: AuthorizationPolarity
    sentence: str
    evidence_ids: tuple[str, ...] = ()

    @staticmethod
    def from_mapping(value: Any, sentence: str = "") -> "AuthorizationClaimCandidate | None":
        if not isinstance(value, dict):
            return None
        raw_kind=str(value.get("kind") or AuthorizationClaimKind.AUTHORIZATION_REQUIREMENT.value).upper()
        raw_polarity=str(value.get("polarity") or AuthorizationPolarity.REQUIRED.value).upper()
        try:
            kind=AuthorizationClaimKind(raw_kind)
            polarity=AuthorizationPolarity(raw_polarity)
        except ValueError:
            return None
        concept=value.get("concept")
        concept=str(concept).upper() if concept is not None else None
        ids=value.get("evidence_ids") or []
        if not isinstance(ids,list) or not all(isinstance(item,str) for item in ids):
            return None
        return AuthorizationClaimCandidate(kind,concept,polarity,
            str(value.get("sentence") or sentence),tuple(ids))


class AuthorizationVerificationStatus(str, Enum):
    VERIFIED="VERIFIED"
    INSUFFICIENT_FACTS="INSUFFICIENT_FACTS"
    INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"
    UNKNOWN_REGULATORY_REQUIREMENT="UNKNOWN_REGULATORY_REQUIREMENT"
    CONFLICTING_EVIDENCE="CONFLICTING_EVIDENCE"


@dataclass(frozen=True)
class AuthorizationVerification:
    status: AuthorizationVerificationStatus
    renderable: bool
    reason_codes: tuple[str, ...]
    candidates: tuple[AuthorizationClaimCandidate, ...] = ()
    supported_evidence_ids: tuple[str, ...] = ()


def fact_status(value: Any, default: FactStatus=FactStatus.UNKNOWN) -> FactStatus:
    if isinstance(value, dict):
        raw=value.get("status", default.value)
    else:
        raw=default.value
    try:
        return FactStatus(str(raw).upper())
    except ValueError:
        return FactStatus.UNKNOWN