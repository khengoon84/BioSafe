import re, uuid
from typing import List, Dict, Optional
from cra_contracts_v0_1 import (
    TaskFrame, InteractionResult, InteractionType, CaseState, FactStatus
)

DOMAIN_PATTERNS = {
    "form_e": [
        r"\bform\s*e\b", r"\bnotification\b.*\b(?:lmo|gmm|modified|recombinant)\b",
        r"\bdirector general\b.*\bnotification\b"
    ],
    "lmo_modern_biotechnology": [
        r"\blmo\b", r"\bgmm\b", r"\bgenetically modified\b", r"\brecombinant\b",
        r"\bmodern biotechnology\b"
    ],
    "transport": [
        r"\btransport\b", r"\bshipping\b", r"\bship\b", r"\bcourier\b",
        r"\bpackag(?:e|ing)\b.*\b(?:specimen|infectious|sample)\b"
    ],
    "waste": [
        r"\bwaste\b", r"\bdispos(?:e|al)\b", r"\bsw404\b", r"\bscheduled waste\b"
    ],
    "containment": [
        r"\bcontainment\b", r"\bbiosafety level\b", r"\bbsl[- ]?[1234]\b",
        r"\bbiological safety cabinet\b", r"\bbsc\b", r"\bppe\b"
    ],
    "clinical_specimen": [
        r"\bclinical specimen\b", r"\bpatient specimen\b", r"\bclinical sample\b"
    ],
    "biosecurity": [
        r"\bbiosecurity\b", r"\bdual[- ]use\b"
    ],
    "general_biosafety": [
        r"\bbiosafety\b", r"\brisk assessment\b", r"\blaboratory risk\b",
        r"\bsafety requirement\b"
    ],
    "document_review": [
        r"\breview\b.*\b(?:sop|proposal|protocol|document|risk assessment)\b",
        r"\bcheck\b.*\b(?:sop|proposal|protocol|document)\b"
    ],
}

DECISION_PATTERNS = {
    "form_e_applicability": [r"\b(?:need|require|must|apply|applicable)\b.*\bform\s*e\b"],
    "notification_applicability": [r"\b(?:need|require|must)\b.*\bnotif(?:y|ication)\b"],
    "containment_requirement": [r"\b(?:containment|bsl|biosafety level|bsc|ppe)\b"],
    "transport_requirement": [r"\b(?:transport|ship|shipping|courier)\b"],
    "waste_requirement": [r"\b(?:waste|dispose|disposal|sw404)\b"],
    "general_biosafety_requirement": [r"\bbiosafety requirement\b", r"\bwhat.*biosafety\b"],
}

def _match_domains(text: str) -> List[str]:
    out=[]
    for domain,patterns in DOMAIN_PATTERNS.items():
        if any(re.search(p,text,re.I) for p in patterns):
            out.append(domain)
    return out

def _match_decisions(text: str) -> List[str]:
    out=[]
    for decision,patterns in DECISION_PATTERNS.items():
        if any(re.search(p,text,re.I) for p in patterns):
            out.append(decision)
    return out

def _known_facts(case: CaseState) -> List[str]:
    out=[]
    for name,fact in case.facts.items():
        if fact.status not in {FactStatus.UNKNOWN, FactStatus.DISPUTED} and fact.value is not None:
            out.append(f"{name}={fact.value}")
    if case.jurisdiction.status not in {FactStatus.UNKNOWN, FactStatus.DISPUTED} and case.jurisdiction.value:
        out.append(f"jurisdiction={case.jurisdiction.value}")
    return out

def build_task_frame(
    user_text: str,
    interaction: InteractionResult,
    case: CaseState,
    resolved_reference: Optional[str]=None,
    task_id: Optional[str]=None,
) -> TaskFrame:
    text=(user_text or "").strip()
    requested=_match_domains(text)

    # Product/social/reformulation turns do not activate regulatory domains.
    if interaction.interaction_type in {
        InteractionType.SOCIAL, InteractionType.PRODUCT_HELP, InteractionType.REFORMULATE
    }:
        activated=[]
    elif interaction.interaction_type == InteractionType.FOLLOW_UP:
        # A referential follow-up should inherit only currently active case domains;
        # it must not activate a new domain merely from a generic noun such as "approval".
        activated=list(case.active_domains)
    elif interaction.interaction_type == InteractionType.CLARIFICATION_RESPONSE:
        activated=list(case.active_domains)
    elif interaction.interaction_type == InteractionType.TASK_CHANGE:
        activated=list(requested)
    else:
        activated=list(requested)

    # If a new domain question says only "biosafety requirement", keep it general.
    if "general_biosafety" in activated and not any(
        d in activated for d in ["form_e","transport","waste","lmo_modern_biotechnology","clinical_specimen","biosecurity"]
    ):
        activated=[d for d in activated if d not in ["form_e","transport","waste"]]

    known=_known_facts(case)
    unknowns=list(case.open_questions)

    decisions=_match_decisions(text)
    if interaction.interaction_type == InteractionType.FOLLOW_UP and resolved_reference:
        decisions=["explain_previous_concept"]

    all_special={"form_e","lmo_modern_biotechnology","transport","waste","containment","clinical_specimen","biosecurity"}
    inactive=sorted((set(case.inactive_domains) | (all_special-set(activated))) - set(activated))

    goal=interaction.candidate_task or "answer_user_question"
    expectations=[]
    if interaction.interaction_type == InteractionType.FOLLOW_UP:
        expectations.append("answer the referenced prior concept directly")
    if interaction.interaction_type == InteractionType.CLARIFICATION_RESPONSE:
        expectations.append("update the pending fact before any downstream decision")
    if interaction.interaction_type == InteractionType.PRODUCT_HELP:
        expectations.append("provide product help without regulatory retrieval")

    return TaskFrame(
        task_id=task_id or f"task-{uuid.uuid4().hex[:8]}",
        interaction_type=interaction.interaction_type,
        user_goal=goal,
        current_question=text,
        jurisdiction=case.jurisdiction.value if case.jurisdiction.value else None,
        known_facts=known,
        relevant_unknowns=unknowns,
        requested_domains=requested,
        activated_domains=sorted(set(activated)),
        inactive_domains=inactive,
        decisions_requested=decisions,
        decisions_not_requested=[],
        response_expectations=expectations,
    )
