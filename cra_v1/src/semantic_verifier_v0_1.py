import re
from typing import List, Dict, Any, Optional, Set
from cra_contracts_v0_1 import (
    CaseState, TaskFrame, DecisionNode, DecisionStatus, VerificationResult, FactStatus
)

PROHIBITED_CERTIFICATION_PATTERNS = [
    r"\byou are compliant\b",
    r"\bthis is compliant\b",
    r"\byou are not compliant\b",
    r"\bthis is not compliant\b",
    r"\bapproved\b",
    r"\bnot approved\b",
    r"\bcertified\b",
    r"\bofficially compliant\b",
    r"\bmeets all legal requirements\b",
    r"\bdoes not meet legal requirements\b",
]

MANDATORY_WORDS = re.compile(r"\b(must|required|mandatory|compulsory|shall|need to)\b", re.I)

class SemanticVerificationError(ValueError):
    pass

def _claim_text(payload: Dict[str,Any]) -> str:
    chunks=[]
    for key in ["direct_answer","conclusion","reason"]:
        v=payload.get(key)
        if isinstance(v,str):
            chunks.append(v)
    for key in ["recommendations","recommended_next_steps","educational_points"]:
        v=payload.get(key)
        if isinstance(v,list):
            chunks.extend(str(x) for x in v)
    return " ".join(chunks)

def _fact_values(case: CaseState) -> Dict[str,Any]:
    out={}
    if case.jurisdiction.value is not None:
        out["jurisdiction"]=case.jurisdiction.value
    for name,f in case.facts.items():
        if f.status not in {FactStatus.UNKNOWN, FactStatus.DISPUTED} and f.value is not None:
            out[name]=f.value
    return out

def _has_unknown_promotion(payload: Dict[str,Any], case: CaseState) -> bool:
    text=_claim_text(payload).lower()
    for name,fact in case.facts.items():
        if fact.status in {FactStatus.UNKNOWN, FactStatus.DISPUTED} or fact.value is None:
            label=name.replace("_"," ").lower()
            # If an unresolved fact is expressed as an asserted equality-ish phrase, flag it.
            patterns = [
                rf"\b{re.escape(label)}\s+(?:is|=)\s+",
                rf"\bthe\s+{re.escape(label)}\s+(?:is|=)\s+",
            ]
            if any(re.search(p,text) for p in patterns):
                return True
    return False

def _contradicts_confirmed_fact(payload: Dict[str,Any], case: CaseState) -> bool:
    text=_claim_text(payload).lower()
    for name,fact in case.facts.items():
        if fact.status == FactStatus.USER_CONFIRMED and isinstance(fact.value,bool):
            label=name.replace("_"," ").lower()
            if fact.value is False and re.search(rf"\b{re.escape(label)}\s+is\s+(?:true|yes|present|applicable)\b",text):
                return True
            if fact.value is True and re.search(rf"\b{re.escape(label)}\s+is\s+(?:false|no|absent|not applicable)\b",text):
                return True
    return False

def verify_response(
    frame: TaskFrame,
    case: CaseState,
    decisions: List[DecisionNode],
    payload: Dict[str,Any],
    evidence_catalog: Optional[Dict[str,Dict[str,Any]]] = None,
) -> VerificationResult:
    evidence_catalog=evidence_catalog or {}
    checks={}

    # V-01 prerequisite sufficiency
    prereq_ok=True
    for d in decisions:
        unsatisfied=[p for p in d.prerequisites if not p.satisfied]
        if unsatisfied and d.status not in {
            DecisionStatus.INSUFFICIENT_INFORMATION,
            DecisionStatus.CONFLICTING_EVIDENCE,
            DecisionStatus.REQUIRES_HUMAN_REVIEW
        }:
            prereq_ok=False
    checks["prerequisite_sufficiency"]=prereq_ok

    # V-02 citation support / entailment proxy:
    # every substantive regulatory decision must point to evidence entries that declare support for its decision_type.
    citation_ok=True
    for d in decisions:
        if d.status in {DecisionStatus.SUPPORTED,DecisionStatus.NOT_SUPPORTED,DecisionStatus.NOT_APPLICABLE}:
            if not d.evidence_ids or not d.authority_refs:
                citation_ok=False
                break
            for eid in d.evidence_ids:
                meta=evidence_catalog.get(eid)
                if not meta:
                    citation_ok=False
                    break
                supports=set(meta.get("supports_decision_types",[]))
                if d.decision_type not in supports:
                    citation_ok=False
                    break
            if not citation_ok:
                break
    checks["citation_support"]=citation_ok

    # V-03 jurisdiction match
    jurisdiction_ok=True
    expected=frame.jurisdiction
    if expected:
        for d in decisions:
            for eid in d.evidence_ids:
                meta=evidence_catalog.get(eid,{})
                ej=meta.get("jurisdiction")
                if ej and ej not in {expected,"International","Global"}:
                    jurisdiction_ok=False
    checks["jurisdiction_match"]=jurisdiction_ok

    # V-04 currentness
    current_ok=True
    for d in decisions:
        for eid in d.evidence_ids:
            meta=evidence_catalog.get(eid,{})
            if meta.get("status")=="superseded":
                current_ok=False
    checks["currentness"]=current_ok

    # V-05 domain activation
    active=set(frame.activated_domains)
    domain_ok=True
    for d in decisions:
        required=set()
        for eid in d.evidence_ids:
            required.update(evidence_catalog.get(eid,{}).get("domains",[]))
        # general_biosafety may support specialized domains, but specialized domains
        # must not appear unless explicitly active.
        specialized={x for x in required if x in {
            "form_e","lmo_modern_biotechnology","transport","waste",
            "clinical_specimen","biosecurity","containment"
        }}
        if not specialized.issubset(active):
            domain_ok=False
            break
    payload_domains=set(payload.get("domains_mentioned",[]))
    specialized_payload={x for x in payload_domains if x in {
        "form_e","lmo_modern_biotechnology","transport","waste",
        "clinical_specimen","biosecurity","containment"
    }}
    if not specialized_payload.issubset(active):
        domain_ok=False
    checks["domain_activation"]=domain_ok

    # V-06 state consistency
    checks["state_consistency"]=not _contradicts_confirmed_fact(payload,case)

    # V-07 unknown preservation
    checks["unknown_preservation"]=not _has_unknown_promotion(payload,case)

    # V-08 no certification / approval determination
    text=_claim_text(payload)
    checks["no_certification"]=not any(re.search(p,text,re.I) for p in PROHIBITED_CERTIFICATION_PATTERNS)

    # V-09 recommendation support
    recommendation_ok=True
    recommendations=payload.get("recommended_next_steps",[]) or payload.get("recommendations",[])
    if recommendations:
        supported_actions=set()
        for d in decisions:
            for eid in d.evidence_ids:
                supported_actions.update(evidence_catalog.get(eid,{}).get("supports_actions",[]))
        for rec in recommendations:
            rec_text=str(rec).lower()
            if MANDATORY_WORDS.search(rec_text):
                # mandatory recommendation must have at least one explicit supported action
                if not supported_actions:
                    recommendation_ok=False
                    break
    checks["recommendation_support"]=recommendation_ok

    # V-10 turn relevance
    relevance_ok=True
    expected=frame.response_expectations
    answer_target=payload.get("answer_target")
    if "answer the referenced prior concept directly" in expected:
        relevance_ok = bool(answer_target and answer_target=="referential_follow_up")
    if "provide product help without regulatory retrieval" in expected:
        relevance_ok = relevance_ok and payload.get("response_type")=="product_help"
    checks["turn_relevance"]=relevance_ok

    issues=[]
    warnings=[]
    for name,passed in checks.items():
        if not passed:
            issues.append(name)

    decision="PASS" if all(checks.values()) else "FAIL"
    return VerificationResult(decision=decision,checks=checks,issues=issues,warnings=warnings)
