from dataclasses import dataclass
from typing import Dict, Any, Optional, Callable
from cra_contracts_v0_1 import *
from interaction_state_engine_v0_1 import process_turn
from task_frame_builder_v0_1 import build_task_frame
from evidence_requirement_planner_v0_1 import plan_evidence
from retrieval_request_adapter_v0_1 import build_retrieval_request
from semantic_verifier_v0_1 import verify_response
from researcher_response_composer_v0_1 import compose_response_plan, render_response

@dataclass
class CRAIntegrationResult:
    interaction: InteractionResult
    task_frame: TaskFrame
    evidence_plan: EvidencePlan
    retrieval_request: Dict[str,Any]
    rendered_response: Optional[Dict[str,Any]]
    route: str

def product_help_answer(text: str) -> str:
    t=text.lower()
    if "who are you" in t or "what are you" in t:
        return "I’m BioSafe, a local biosafety and biosecurity assistant designed to support researchers with biosafety questions, document review, and researcher-facing Form E assistance."
    if "document" in t or "review" in t:
        return "I can review biosafety-related SOPs, research proposals, protocols, risk-assessment material, and researcher-facing Form E drafts for gaps, missing information, and internal consistency."
    if "form e" in t:
        return "The Form E Assistant helps map information you provide into the researcher-facing Form E workflow, identifies missing information, and checks consistency. It does not simulate IBC approval or regulatory approval."
    return "I can help with biosafety and biosecurity questions, document review, risk-assessment support, and researcher-facing Form E assistance."

def integrate_turn(
    text: str,
    turn_id: str,
    conversation: ConversationState,
    case: CaseState,
    domain_callback: Optional[Callable[[TaskFrame,EvidencePlan,Dict[str,Any]],Dict[str,Any]]]=None,
) -> CRAIntegrationResult:
    turn=process_turn(text,turn_id,conversation,case)
    frame=build_task_frame(text,turn.interaction,turn.case_state,resolved_reference=turn.resolved_reference)
    evidence_plan=plan_evidence(frame)
    retrieval=build_retrieval_request(frame,evidence_plan)

    # Deterministic bypass: product/help and social interactions never enter regulatory RAG.
    if turn.interaction.interaction_type == InteractionType.PRODUCT_HELP:
        verification=VerificationResult(
            decision="PASS",
            checks={
                "prerequisite_sufficiency":True,"citation_support":True,
                "jurisdiction_match":True,"currentness":True,
                "domain_activation":True,"state_consistency":True,
                "unknown_preservation":True,"no_certification":True,
                "recommendation_support":True,"turn_relevance":True,
            }
        )
        plan=compose_response_plan(
            frame,[],verification,
            product_help=True,
            direct_answer_hint=product_help_answer(text)
        )
        return CRAIntegrationResult(turn.interaction,frame,evidence_plan,retrieval,render_response(plan),"product_help_bypass")

    if turn.interaction.interaction_type == InteractionType.SOCIAL:
        return CRAIntegrationResult(turn.interaction,frame,evidence_plan,retrieval,
            {"response_type":"simple_answer","direct_answer":"Hello. How can I help with your biosafety work?","sections":[]},"social_bypass")

    if turn.interaction.interaction_type == InteractionType.REFORMULATE:
        return CRAIntegrationResult(turn.interaction,frame,evidence_plan,retrieval,None,"conversation_context_required")

    # Domain pipeline remains an adapter boundary in v0.1.
    # Existing frozen RAG/inference can be called here in the next integration step.
    if domain_callback is None:
        return CRAIntegrationResult(turn.interaction,frame,evidence_plan,retrieval,None,"domain_adapter_pending")

    payload=domain_callback(frame,evidence_plan,retrieval)
    return CRAIntegrationResult(turn.interaction,frame,evidence_plan,retrieval,payload,"domain_adapter")
