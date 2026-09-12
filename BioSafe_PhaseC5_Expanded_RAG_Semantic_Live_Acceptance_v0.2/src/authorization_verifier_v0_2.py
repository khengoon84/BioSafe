from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from authorization_contracts_v0_2 import (
    AuthorizationClaimCandidate, AuthorizationClaimKind, AuthorizationPolarity,
    AuthorizationVerification, AuthorizationVerificationStatus, FactStatus, fact_status,
)

HERE=Path(__file__).resolve().parent
ONTOLOGY_PATH=HERE/"authorization_ontology_v0_2.json"
FAIL_CLOSED_MESSAGE=(
    "BioSafe cannot determine whether a regulatory authorization is required for this activity "
    "without sufficient project-specific facts and reviewed evidence."
)
TEXT_FIELDS=("conclusion","direct_answer")
LIST_FIELDS=("recommended_next_step","recommendations","recommended_next_steps","missing_information")
SENTENCE_SPLIT=re.compile(r"(?<=[.!?])\s+")


def load_ontology(path: Path=ONTOLOGY_PATH) -> dict[str, Any]:
    data=json.loads(path.read_text(encoding="utf-8"))
    required=("authorization_concepts","normative_force_terms","governance_action_terms",
              "governance_actor_terms","required_fact_names")
    missing=[key for key in required if not data.get(key)]
    if missing:
        raise ValueError(f"authorization ontology missing keys: {sorted(missing)}")
    return data


_ONTOLOGY_CACHE: dict[str, Any] | None=None


def _ontology() -> dict[str, Any]:
    global _ONTOLOGY_CACHE
    if _ONTOLOGY_CACHE is None:
        _ONTOLOGY_CACHE=load_ontology()
    return _ONTOLOGY_CACHE


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in SENTENCE_SPLIT.split(text or "") if item.strip()]


def _concepts(sentence: str) -> list[str]:
    text=sentence.lower()
    return [name for name, spec in _ontology()["authorization_concepts"].items()
            if any(re.search(rf"\b{re.escape(term)}\b", text) for term in spec["surface_terms"])]


def _normative(sentence: str) -> bool:
    text=sentence.lower()
    return any(term in text for term in _ontology()["normative_force_terms"])


def _governance(sentence: str) -> bool:
    text=sentence.lower()
    terms=_ontology()["governance_action_terms"]+_ontology()["governance_actor_terms"]
    return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)


def _candidate(sentence: str) -> AuthorizationClaimCandidate | None:
    concepts=_concepts(sentence)
    if not _normative(sentence):
        return None
    polarity=(AuthorizationPolarity.NOT_REQUIRED if re.search(r"\b(?:no|not|without|do not|does not)\b", sentence, re.I)
              else AuthorizationPolarity.REQUIRED)
    if concepts:
        return AuthorizationClaimCandidate(AuthorizationClaimKind.AUTHORIZATION_REQUIREMENT,
            concepts[0],polarity,sentence)
    if _governance(sentence):
        return AuthorizationClaimCandidate(AuthorizationClaimKind.UNKNOWN_REGULATORY_REQUIREMENT,
            None,polarity,sentence)
    return None


def _evidence_supports(candidate: AuthorizationClaimCandidate, evidence: list[dict[str, Any]]) -> tuple[bool, tuple[str, ...]]:
    if candidate.concept is None:
        return False, ()
    allowed=set(_ontology()["authorization_concepts"][candidate.concept]["support_claim_types"])
    matched=[]
    for item in evidence:
        if str(item.get("claim_type") or "").lower() in allowed and not item.get("claim_type") in _ontology().get("excluded_support_claim_types",[]):
            matched.append(str(item.get("evidence_id") or ""))
    return bool(matched), tuple(x for x in matched if x)


def parse_structured_claims(value: Any) -> tuple[AuthorizationClaimCandidate, ...] | None:
    """Parse the untrusted model claim channel without granting it authority."""
    if value is None:
        return ()
    if not isinstance(value,list):
        return None
    parsed=[]
    for item in value:
        candidate=AuthorizationClaimCandidate.from_mapping(item)
        if candidate is None:
            return None
        parsed.append(candidate)
    return tuple(parsed)


def verify_structured_claims(value: Any, evidence: list[dict[str, Any]] | None=None,
                             case_state: dict[str, Any] | None=None) -> AuthorizationVerification:
    parsed=parse_structured_claims(value)
    if parsed is None:
        return AuthorizationVerification(AuthorizationVerificationStatus.INSUFFICIENT_EVIDENCE,False,
            ("INVALID_STRUCTURED_AUTHORIZATION_CLAIMS",))
    if not parsed:
        return AuthorizationVerification(AuthorizationVerificationStatus.VERIFIED,True,())
    unknown=tuple(item for item in parsed if item.kind is AuthorizationClaimKind.UNKNOWN_REGULATORY_REQUIREMENT
                  or item.concept not in _ontology()["authorization_concepts"])
    if unknown:
        return AuthorizationVerification(AuthorizationVerificationStatus.UNKNOWN_REGULATORY_REQUIREMENT,False,
            ("UNKNOWN_AUTHORIZATION_CONCEPT",),unknown)
    if not _facts_complete(case_state):
        return AuthorizationVerification(AuthorizationVerificationStatus.INSUFFICIENT_FACTS,False,
            ("AUTHORIZATION_FACTS_NOT_VERIFIED",),parsed)
    supported=[]
    for candidate in parsed:
        ok,ids=_evidence_supports(candidate,evidence or [])
        requested=set(candidate.evidence_ids)
        if requested and not requested.issubset(set(ids)):
            ok=False
        if not ok:
            return AuthorizationVerification(AuthorizationVerificationStatus.INSUFFICIENT_EVIDENCE,False,
                ("NO_COMPATIBLE_TYPED_EVIDENCE",),parsed,tuple(supported))
        supported.extend(ids)
    return AuthorizationVerification(AuthorizationVerificationStatus.VERIFIED,True,(),parsed,tuple(supported))


def render_verified_authorization_claims(verification: AuthorizationVerification) -> str:
    """Render only claims that passed structured evidence verification."""
    if not verification.renderable or not verification.candidates:
        return ""
    labels={"PERMIT":"permit","LICENCE":"licence","APPROVAL":"approval",
            "AUTHORIZATION":"authorization","EXEMPTION":"exemption","NOTIFICATION":"notification",
            "REGISTRATION":"registration","CLEARANCE":"clearance","CONSENT":"consent","CERTIFICATE":"certificate"}
    rendered=[]
    for candidate in verification.candidates:
        noun=labels.get(candidate.concept or "",(candidate.concept or "authorization").lower())
        if candidate.polarity is AuthorizationPolarity.NOT_REQUIRED:
            rendered.append(f"The reviewed evidence supports that no specific {noun} requirement applies to this case.")
        else:
            rendered.append(f"The reviewed evidence supports that a {noun} requirement applies to this case.")
    return " ".join(rendered)


def _facts_complete(case_state: dict[str, Any] | None) -> bool:
    state=case_state or {}
    for name in _ontology()["required_fact_names"]:
        value=state.get(name)
        # A bare scalar is not provenance-bearing. Facts must arrive as an
        # explicit structured record so query extraction cannot silently become
        # a confirmed case fact.
        status=fact_status(value,FactStatus.UNKNOWN)
        if status not in (FactStatus.USER_ASSERTED,FactStatus.VERIFIED):
            return False
        raw=value.get("value") if isinstance(value,dict) else value
        if raw in (None,"", "unknown", "unspecified"):
            return False
    return True


def verify_authorization_claims(text: str, evidence: list[dict[str, Any]] | None=None,
                                case_state: dict[str, Any] | None=None) -> AuthorizationVerification:
    evidence=evidence or []
    candidates=tuple(candidate for sentence in _sentences(text) if (candidate:=_candidate(sentence)))
    if not candidates:
        return AuthorizationVerification(AuthorizationVerificationStatus.VERIFIED,True,(),())
    unknown=tuple(item for item in candidates
                  if item.kind is AuthorizationClaimKind.UNKNOWN_REGULATORY_REQUIREMENT)
    if unknown:
        return AuthorizationVerification(AuthorizationVerificationStatus.UNKNOWN_REGULATORY_REQUIREMENT,False,
            ("UNKNOWN_AUTHORIZATION_CONCEPT",),unknown)
    if not _facts_complete(case_state):
        return AuthorizationVerification(AuthorizationVerificationStatus.INSUFFICIENT_FACTS,False,
            ("AUTHORIZATION_FACTS_NOT_VERIFIED",),candidates)
    supported=[]
    for candidate in candidates:
        ok,ids=_evidence_supports(candidate,evidence)
        if not ok:
            status=(AuthorizationVerificationStatus.UNKNOWN_REGULATORY_REQUIREMENT
                    if candidate.kind is AuthorizationClaimKind.UNKNOWN_REGULATORY_REQUIREMENT
                    else AuthorizationVerificationStatus.INSUFFICIENT_EVIDENCE)
            return AuthorizationVerification(status,False,
                (("UNKNOWN_AUTHORIZATION_CONCEPT",) if candidate.concept is None else ("NO_COMPATIBLE_TYPED_EVIDENCE",)),
                candidates,tuple(supported))
        supported.extend(ids)
    return AuthorizationVerification(AuthorizationVerificationStatus.VERIFIED,True,(),candidates,tuple(supported))


def _case_state_for_verification(case_state: dict[str, Any] | None) -> dict[str, Any]:
    return case_state or {}


def apply_universal_authorization_verifier(response: dict[str, Any],
                                           evidence: list[dict[str, Any]] | None=None,
                                           case_state: dict[str, Any] | None=None,
                                           structured_claims: Any=None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Universal final screen. Prose can create candidates, never authority."""
    out=deepcopy(response); evidence=evidence if evidence is not None else list(out.get("evidence") or [])
    audit=[]
    verifications=[]
    structured_verification=verify_structured_claims(structured_claims,evidence,case_state) if structured_claims is not None else None
    if structured_verification is not None:
        verifications.append(structured_verification)
        if not structured_verification.renderable:
            out["conclusion"]=FAIL_CLOSED_MESSAGE
            audit.append({"action":"withhold_invalid_or_unverified_structured_authorization_claims",
                          "field":"authorization_claim_candidates",
                          "status":structured_verification.status.value,
                          "reason_codes":list(structured_verification.reason_codes),
                          "claims":[candidate.sentence for candidate in structured_verification.candidates]})
    for field in TEXT_FIELDS:
        value=out.get(field)
        if not isinstance(value,str) or not value.strip():
            continue
        verification=(structured_verification if structured_verification is not None and structured_verification.candidates
                      else verify_authorization_claims(value,evidence,_case_state_for_verification(case_state)))
        verifications.append(verification)
        if verification.renderable:
            if structured_verification is not None and structured_verification.candidates:
                rendered=render_verified_authorization_claims(verification)
                if rendered:
                    out[field]=rendered
            continue
        out[field]=FAIL_CLOSED_MESSAGE
        audit.append({"action":"withhold_unverified_authorization_claim","field":field,
                      "status":verification.status.value,"reason_codes":list(verification.reason_codes),
                      "claims":[candidate.sentence for candidate in verification.candidates]})
    for field in LIST_FIELDS[:-1]:
        value=out.get(field)
        if not isinstance(value,list):
            continue
        kept=[]
        for item in value:
            if not isinstance(item,str):
                kept.append(item); continue
            verification=verify_authorization_claims(item,evidence,_case_state_for_verification(case_state))
            verifications.append(verification)
            if verification.renderable:
                kept.append(item)
            else:
                audit.append({"action":"withhold_unverified_authorization_claim","field":field,
                              "status":verification.status.value,"reason_codes":list(verification.reason_codes),
                              "claims":[candidate.sentence for candidate in verification.candidates]})
        out[field]=kept
    if verifications:
        chosen=next((item for item in verifications if not item.renderable),verifications[0])
        has_candidates=any(item.candidates for item in verifications)
        structured_invalid=(structured_verification is not None and
                            not structured_verification.renderable)
        out["authorization_assessment"]={
            "status":chosen.status.value if (has_candidates or structured_invalid) else "NO_CLAIM",
            "renderable":chosen.renderable,
            "reason_codes":list(chosen.reason_codes),
            "candidate_count":sum(len(item.candidates) for item in verifications),
            "supported_evidence_ids":list(chosen.supported_evidence_ids),
        }
    else:
        out["authorization_assessment"]={"status":"NO_CLAIM","renderable":True,
                                          "reason_codes":[],"candidate_count":0,
                                          "supported_evidence_ids":[]}
    if audit:
        safety=dict(out.get("safety") or {})
        safety["status"]="FAIL_CLOSED"; safety["response_mode"]="ask_before_concluding"
        codes=list(safety.get("reason_codes") or [])+(["UNVERIFIED_AUTHORIZATION_CLAIM_WITHHELD"])
        safety["reason_codes"]=list(dict.fromkeys(codes)); out["safety"]=safety
        meta=dict(out.get("_meta") or {})
        meta["authorization_verifier"]=audit; out["_meta"]=meta
    return out,audit