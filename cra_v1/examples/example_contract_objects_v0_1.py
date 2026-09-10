from cra_contracts_v0_1 import *

product_help = InteractionResult(
    interaction_type=InteractionType.PRODUCT_HELP,
    confidence=0.99,
    candidate_task="explain_document_review_capability",
    needs_domain_pipeline=False,
)

conversation = ConversationState(
    session_id="demo-session",
    current_topic="biosafety requirement assessment",
    active_interaction=InteractionType.CLARIFICATION_RESPONSE,
    pending_clarifications=[
        PendingClarification(
            field="organism_identity",
            question="Please confirm the organism name.",
            turn_id="t2",
        )
    ],
)

case = CaseState(
    case_id="demo-case",
    jurisdiction=FactValue(value="Malaysia", status=FactStatus.USER_CONFIRMED, source="user"),
    facts={
        "organism_identity": FactValue(
            value="Bacillus anthracis",
            status=FactStatus.USER_CONFIRMED,
            source="user clarification",
            confidence=1.0,
        ),
        "lmo_status": FactValue(
            value=None,
            status=FactStatus.UNKNOWN,
            source=None,
        ),
    },
    active_domains=["general_biosafety"],
    inactive_domains=["transport","waste"],
    open_questions=["lmo_status","activity_type"],
)

task = TaskFrame(
    task_id="task-001",
    interaction_type=InteractionType.FOLLOW_UP,
    user_goal="understand the biosafety requirement",
    current_question="What did you mean by regulatory approval?",
    jurisdiction="Malaysia",
    known_facts=["organism_identity=Bacillus anthracis"],
    relevant_unknowns=["lmo_status","activity_type"],
    requested_domains=["general_biosafety"],
    activated_domains=["general_biosafety"],
    inactive_domains=["transport","waste"],
    decisions_requested=["explain_previous_regulatory_concept"],
    decisions_not_requested=["transport_classification","waste_pathway"],
    response_expectations=["answer the referential follow-up directly"],
)

evidence = EvidencePlan(
    skip_rag=False,
    required_domains=["malaysia_biosafety_regulatory_context"],
    required_evidence_types=["definition","scope"],
    preferred_authority_tiers=[1,2],
    exclude_domains=["transport","waste"],
    jurisdiction="Malaysia",
)

lmo_decision = DecisionNode(
    decision_id="DEC-LMO-001",
    decision_type="malaysia_lmo_notification_applicability",
    status=DecisionStatus.INSUFFICIENT_INFORMATION,
    prerequisites=[
        PrerequisiteResult("jurisdiction_established", True, ["jurisdiction"]),
        PrerequisiteResult("lmo_trigger_established", False, ["lmo_status"]),
        PrerequisiteResult("activity_type_established", False, ["activity_type"]),
    ],
    unresolved_dependencies=["lmo_status","activity_type"],
    reason="LMO/modern-biotechnology status and activity type are not established.",
)

response = ResponsePlan(
    response_type=ResponseType.NEEDS_CLARIFICATION,
    direct_answer="I can explain the regulatory pathway, but I cannot determine whether it applies to your activity until the modification status and activity type are known.",
    why_this_matters=["Species identity alone does not establish LMO status or a notification pathway."],
    clarification_questions=[
        "Is the material genetically modified, recombinant, or otherwise produced using modern biotechnology?",
        "What activity are you carrying out with the material?"
    ],
    recommended_next_steps=["Confirm those two facts before applying an LMO-specific notification pathway."],
    source_refs=["CLM-005"],
)
