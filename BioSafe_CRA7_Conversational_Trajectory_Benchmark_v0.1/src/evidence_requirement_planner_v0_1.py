from cra_contracts_v0_1 import EvidencePlan, InteractionType, TaskFrame

DOMAIN_EVIDENCE = {
    "general_biosafety": ["risk_assessment","general_biosafety_guidance"],
    "containment": ["risk_assessment","containment_guidance"],
    "lmo_modern_biotechnology": ["definition","applicability_scope","notification_scope"],
    "form_e": ["lmo_applicability","notification_scope","form_e_researcher_fields"],
    "transport": ["transport_classification","packaging_transport_guidance"],
    "waste": ["waste_classification","disposal_requirements"],
    "clinical_specimen": ["clinical_specimen_handling"],
    "biosecurity": ["biosecurity_guidance"],
    "document_review": ["applicable_review_criteria"],
}

def plan_evidence(frame: TaskFrame) -> EvidencePlan:
    if frame.interaction_type in {
        InteractionType.SOCIAL, InteractionType.PRODUCT_HELP, InteractionType.REFORMULATE
    }:
        return EvidencePlan(
            skip_rag=True,
            required_domains=[],
            required_evidence_types=[],
            preferred_authority_tiers=[],
            exclude_domains=list(frame.inactive_domains),
            jurisdiction=frame.jurisdiction,
        )

    required_domains=list(frame.activated_domains)
    evidence_types=[]
    for d in required_domains:
        evidence_types.extend(DOMAIN_EVIDENCE.get(d,[]))

    # Referential follow-up with no active domain should not invent a regulatory search.
    if frame.interaction_type == InteractionType.FOLLOW_UP and not required_domains:
        return EvidencePlan(
            skip_rag=True,
            required_domains=[],
            required_evidence_types=[],
            preferred_authority_tiers=[],
            exclude_domains=list(frame.inactive_domains),
            jurisdiction=frame.jurisdiction,
        )

    return EvidencePlan(
        skip_rag=(len(required_domains)==0),
        required_domains=sorted(set(required_domains)),
        required_evidence_types=sorted(set(evidence_types)),
        preferred_authority_tiers=[1,2] if required_domains else [],
        exclude_domains=sorted(set(frame.inactive_domains)-set(required_domains)),
        jurisdiction=frame.jurisdiction,
    )
