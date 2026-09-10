from cra_contracts_v0_1 import (
    InteractionResult, FactValue, ConversationState, CaseState, TaskFrame,
    EvidencePlan, DecisionNode, VerificationResult, ResponsePlan,
    FactStatus, DecisionStatus, InteractionType, ResponseType
)

class ContractError(ValueError):
    pass

def _assert(cond, msg):
    if not cond:
        raise ContractError(msg)

def validate_interaction(x: InteractionResult):
    _assert(isinstance(x.interaction_type, InteractionType), "invalid interaction_type")
    _assert(0 <= x.confidence <= 1, "confidence must be between 0 and 1")
    if x.interaction_type in {InteractionType.SOCIAL, InteractionType.PRODUCT_HELP}:
        _assert(x.needs_domain_pipeline is False, "social/product help must normally bypass domain pipeline")
    return True

def validate_fact(x: FactValue):
    _assert(isinstance(x.status, FactStatus), "invalid fact status")
    if x.status == FactStatus.UNKNOWN:
        _assert(x.value is None, "unknown fact must not carry an asserted value")
    if x.confidence is not None:
        _assert(0 <= x.confidence <= 1, "fact confidence must be 0..1")
    return True

def validate_conversation_state(x: ConversationState):
    _assert(bool(x.session_id), "session_id required")
    for c in x.pending_clarifications:
        _assert(bool(c.field and c.question and c.turn_id), "pending clarification incomplete")
    return True

def validate_case_state(x: CaseState):
    _assert(bool(x.case_id), "case_id required")
    validate_fact(x.jurisdiction)
    for name, fact in x.facts.items():
        _assert(bool(name), "fact name required")
        validate_fact(fact)
    overlap=set(x.active_domains) & set(x.inactive_domains)
    _assert(not overlap, f"domain cannot be active and inactive: {sorted(overlap)}")
    return True

def validate_task_frame(x: TaskFrame):
    _assert(bool(x.task_id), "task_id required")
    _assert(bool(x.user_goal), "user_goal required")
    _assert(bool(x.current_question), "current_question required")
    overlap=set(x.activated_domains) & set(x.inactive_domains)
    _assert(not overlap, f"task frame has active/inactive domain conflict: {sorted(overlap)}")
    return True

def validate_evidence_plan(x: EvidencePlan):
    if x.skip_rag:
        _assert(not x.required_domains, "skip_rag cannot have required_domains")
        _assert(not x.required_evidence_types, "skip_rag cannot have required_evidence_types")
    overlap=set(x.required_domains) & set(x.exclude_domains)
    _assert(not overlap, f"evidence plan requires and excludes same domain: {sorted(overlap)}")
    return True

def validate_decision_node(x: DecisionNode):
    _assert(bool(x.decision_id), "decision_id required")
    _assert(bool(x.decision_type), "decision_type required")
    _assert(isinstance(x.status, DecisionStatus), "invalid decision status")
    unsat=[p.name for p in x.prerequisites if not p.satisfied]
    if unsat:
        _assert(
            x.status in {
                DecisionStatus.INSUFFICIENT_INFORMATION,
                DecisionStatus.CONFLICTING_EVIDENCE,
                DecisionStatus.REQUIRES_HUMAN_REVIEW
            },
            "decision cannot be supported/not-supported/not-applicable while prerequisites are unsatisfied"
        )
    if x.status == DecisionStatus.INSUFFICIENT_INFORMATION:
        _assert(bool(x.unresolved_dependencies or unsat), "insufficient-information decision must identify unresolved dependency")
    return True

REQUIRED_VERIFIER_CHECKS={
    "prerequisite_sufficiency",
    "citation_support",
    "jurisdiction_match",
    "currentness",
    "domain_activation",
    "state_consistency",
    "unknown_preservation",
    "no_certification",
    "recommendation_support",
    "turn_relevance",
}

def validate_verification_result(x: VerificationResult):
    missing=REQUIRED_VERIFIER_CHECKS-set(x.checks)
    _assert(not missing, f"missing verifier checks: {sorted(missing)}")
    if x.decision == "PASS":
        _assert(all(x.checks.values()), "PASS requires all verifier checks true")
    return True

def validate_response_plan(x: ResponsePlan):
    _assert(isinstance(x.response_type, ResponseType), "invalid response type")
    _assert(bool(x.direct_answer.strip()), "direct_answer required")
    if x.response_type == ResponseType.NEEDS_CLARIFICATION:
        _assert(bool(x.clarification_questions), "needs_clarification requires clarification_questions")
    if x.response_type == ResponseType.PRODUCT_HELP:
        _assert(not x.source_refs, "product_help should not carry regulatory source refs by default")
    return True

def validate_all(**items):
    mapping={
        "interaction": validate_interaction,
        "conversation_state": validate_conversation_state,
        "case_state": validate_case_state,
        "task_frame": validate_task_frame,
        "evidence_plan": validate_evidence_plan,
        "decision_node": validate_decision_node,
        "verification_result": validate_verification_result,
        "response_plan": validate_response_plan,
    }
    for name, obj in items.items():
        if name in mapping:
            mapping[name](obj)
    return True
