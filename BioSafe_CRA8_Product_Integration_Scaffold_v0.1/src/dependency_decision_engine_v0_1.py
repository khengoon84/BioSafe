from pathlib import Path
import json
from typing import Dict, Any, Optional, List, Tuple
from cra_contracts_v0_1 import (
    CaseState, FactValue, FactStatus, DecisionNode, DecisionStatus, PrerequisiteResult
)

SATISFYING_STATUSES = {
    FactStatus.USER_CONFIRMED,
    FactStatus.DOCUMENT_EXTRACTED,
    FactStatus.AUTHORITY_DERIVED,
}

class DependencyEngineError(ValueError):
    pass

def load_dependencies(path=None):
    if path is None:
        path=Path(__file__).resolve().parent.parent/"config"/"decision_dependencies_v0_1.json"
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _get_fact(case: CaseState, name: str, aliases=None):
    aliases=aliases or []
    if name=="jurisdiction":
        return "jurisdiction", case.jurisdiction
    for key in [name]+list(aliases):
        if key in case.facts:
            return key,case.facts[key]
    return name,FactValue()

def _status_allowed(fact: FactValue, allowed):
    allowed=set(allowed or [])
    return fact.status.value in allowed

def evaluate_prerequisite(case: CaseState, spec: Dict[str,Any]) -> Tuple[PrerequisiteResult, Optional[str]]:
    name=spec["fact"]
    ref,fact=_get_fact(case,name,spec.get("aliases"))
    satisfied=False

    if fact.status in {FactStatus.UNKNOWN, FactStatus.DISPUTED, FactStatus.INFERRED, FactStatus.USER_ASSERTED}:
        satisfied=False
    elif not _status_allowed(fact,spec.get("accepted_statuses",[])):
        satisfied=False
    elif "required_value" in spec:
        satisfied=(fact.value == spec["required_value"])
    else:
        # False is a legitimate established value, e.g. lmo_status=False.
        satisfied=(fact.value is not None)

    unresolved=None if satisfied else name
    return PrerequisiteResult(name=name,satisfied=satisfied,fact_refs=[ref] if ref else []),unresolved

def evaluate_decision_readiness(
    decision_type: str,
    case: CaseState,
    authority_refs=None,
    evidence_ids=None,
    specific=False,
    dependency_config=None,
) -> DecisionNode:
    config=dependency_config or load_dependencies()
    if decision_type not in config:
        raise DependencyEngineError(f"unknown decision type: {decision_type}")

    spec=config[decision_type]
    prereqs=[]
    unresolved=[]

    for p in spec.get("prerequisites",[]):
        result,missing=evaluate_prerequisite(case,p)
        prereqs.append(result)
        if missing: unresolved.append(missing)

    if specific:
        for p in spec.get("contextual_prerequisites",[]):
            result,missing=evaluate_prerequisite(case,p)
            prereqs.append(result)
            if missing: unresolved.append(missing)

    # Readiness only establishes whether BioSafe may proceed to authoritative rule evaluation.
    # It does NOT by itself establish applicability, compliance, BSL, approval, or notification.
    if unresolved:
        status=DecisionStatus.INSUFFICIENT_INFORMATION
        reason="Required decision prerequisites are not established: " + ", ".join(sorted(set(unresolved))) + "."
    else:
        status=DecisionStatus.REQUIRES_HUMAN_REVIEW
        reason="Prerequisites are established. Authoritative rule/evidence evaluation is still required before a substantive conclusion."

    return DecisionNode(
        decision_id=f"READY-{decision_type}",
        decision_type=decision_type,
        status=status,
        prerequisites=prereqs,
        authority_refs=list(authority_refs or []),
        evidence_ids=list(evidence_ids or []),
        unresolved_dependencies=sorted(set(unresolved)),
        reason=reason,
    )

def apply_supported_rule(
    readiness: DecisionNode,
    rule_outcome: str,
    authority_refs: List[str],
    evidence_ids: List[str],
    reason: str,
) -> DecisionNode:
    if readiness.status == DecisionStatus.INSUFFICIENT_INFORMATION:
        raise DependencyEngineError("cannot apply a substantive rule while prerequisites are unresolved")
    if not authority_refs or not evidence_ids:
        raise DependencyEngineError("substantive regulatory decision requires authority and evidence")

    allowed={
        "supported":DecisionStatus.SUPPORTED,
        "not_supported":DecisionStatus.NOT_SUPPORTED,
        "not_applicable":DecisionStatus.NOT_APPLICABLE,
        "conflicting_evidence":DecisionStatus.CONFLICTING_EVIDENCE,
        "requires_human_review":DecisionStatus.REQUIRES_HUMAN_REVIEW,
    }
    if rule_outcome not in allowed:
        raise DependencyEngineError("invalid rule outcome")

    return DecisionNode(
        decision_id=readiness.decision_id.replace("READY-","DEC-"),
        decision_type=readiness.decision_type,
        status=allowed[rule_outcome],
        prerequisites=readiness.prerequisites,
        authority_refs=list(authority_refs),
        evidence_ids=list(evidence_ids),
        unresolved_dependencies=[],
        reason=reason,
    )
