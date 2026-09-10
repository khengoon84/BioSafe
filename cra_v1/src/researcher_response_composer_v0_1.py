from typing import List, Dict, Any, Optional
from cra_contracts_v0_1 import (
    ResponsePlan, ResponseType, DecisionNode, DecisionStatus, VerificationResult, TaskFrame
)

class ResponseCompositionError(ValueError):
    pass

def choose_response_type(
    frame: TaskFrame,
    decisions: List[DecisionNode],
    verification: VerificationResult,
    product_help: bool=False,
    document_review: bool=False,
    form_e: bool=False,
    safety_redirect: bool=False,
) -> ResponseType:
    if safety_redirect:
        return ResponseType.SAFETY_REDIRECT
    if product_help:
        return ResponseType.PRODUCT_HELP
    if document_review:
        return ResponseType.DOCUMENT_REVIEW
    if form_e:
        return ResponseType.FORM_E_ASSIST

    if any(d.status == DecisionStatus.INSUFFICIENT_INFORMATION for d in decisions):
        return ResponseType.NEEDS_CLARIFICATION

    if any(d.status in {
        DecisionStatus.SUPPORTED,
        DecisionStatus.NOT_SUPPORTED,
        DecisionStatus.NOT_APPLICABLE,
        DecisionStatus.CONFLICTING_EVIDENCE,
        DecisionStatus.REQUIRES_HUMAN_REVIEW,
    } for d in decisions):
        return ResponseType.REGULATORY_ASSESSMENT

    return ResponseType.SIMPLE_ANSWER

def _dedupe(items: List[str]) -> List[str]:
    seen=set()
    out=[]
    for item in items:
        x=(item or "").strip()
        if not x:
            continue
        key=" ".join(x.lower().split())
        if key not in seen:
            seen.add(key)
            out.append(x)
    return out

def _clarifications_from_decisions(decisions: List[DecisionNode]) -> List[str]:
    questions=[]
    mapping={
        "lmo_status":"Is the material genetically modified, recombinant, or otherwise produced using modern biotechnology?",
        "activity_type":"What activity are you carrying out with the material?",
        "activity_or_procedure":"What procedure or activity are you carrying out?",
        "agent_or_material_identity":"What organism, specimen, or biological material are you working with?",
        "material_identity":"What specimen or biological material is being transported?",
        "transport_context":"What is the transport context (for example, internal transfer, courier shipment, or external transport)?",
        "waste_type":"What type of biological waste is involved?",
        "disposal_context":"How and where is the waste intended to be handled or disposed of?",
        "exposure_route":"What are the plausible exposure routes for the procedure?",
        "scale_or_quantity":"What scale or quantity is involved?",
        "facility_context":"What laboratory/facility context is available for this work?",
    }
    for d in decisions:
        for dep in d.unresolved_dependencies:
            questions.append(mapping.get(dep, f"Please provide: {dep.replace('_',' ')}."))
    return _dedupe(questions)

def _why_this_matters(decisions: List[DecisionNode]) -> List[str]:
    points=[]
    for d in decisions:
        if d.status == DecisionStatus.INSUFFICIENT_INFORMATION:
            if d.decision_type=="malaysia_lmo_notification_applicability":
                points.append("LMO-related notification depends on facts about the modification status and the activity, not on the organism name alone.")
            elif d.decision_type=="containment_assessment":
                points.append("Containment should be matched to the actual work and exposure risks, not inferred from a single label such as organism identity or risk group.")
            elif d.decision_type=="transport_requirement":
                points.append("Transport requirements depend on both the material and how it will be moved.")
            elif d.decision_type=="waste_requirement":
                points.append("Waste handling depends on what the waste is and the disposal context.")
        elif d.status == DecisionStatus.NOT_APPLICABLE:
            points.append("The available facts do not activate that specific regulatory pathway.")
        elif d.status == DecisionStatus.CONFLICTING_EVIDENCE:
            points.append("Conflicting facts or sources need to be resolved before BioSafe can give a stable assessment.")
    return _dedupe(points)

def _default_direct_answer(
    response_type: ResponseType,
    decisions: List[DecisionNode],
    direct_answer_hint: Optional[str]=None,
) -> str:
    if direct_answer_hint and direct_answer_hint.strip():
        return direct_answer_hint.strip()

    if response_type == ResponseType.NEEDS_CLARIFICATION:
        return "I do not have enough confirmed information to make that determination yet."

    if response_type == ResponseType.REGULATORY_ASSESSMENT:
        if not decisions:
            return "I can assess this once the relevant facts and evidence are available."
        d=decisions[0]
        if d.status == DecisionStatus.NOT_APPLICABLE:
            return "Based on the facts currently established, that specific regulatory pathway is not activated."
        if d.status == DecisionStatus.NOT_SUPPORTED:
            return "The available authoritative evidence does not support that conclusion."
        if d.status == DecisionStatus.SUPPORTED:
            return "The available facts and authoritative evidence support this assessment."
        if d.status == DecisionStatus.CONFLICTING_EVIDENCE:
            return "The available information is conflicting, so I cannot give a stable determination yet."
        if d.status == DecisionStatus.REQUIRES_HUMAN_REVIEW:
            return "The prerequisite facts are established, but the authoritative rule evaluation is not complete yet."

    if response_type == ResponseType.PRODUCT_HELP:
        return "I can explain BioSafe's capabilities and supported workflows without running a regulatory assessment."

    if response_type == ResponseType.DOCUMENT_REVIEW:
        return "I can review the document for biosafety gaps, missing information, internal consistency, and alignment with the applicable guidance."

    if response_type == ResponseType.FORM_E_ASSIST:
        return "I can help map available information into the researcher-facing Form E workflow and flag missing information."

    if response_type == ResponseType.SAFETY_REDIRECT:
        return "I can help with the safety, risk-management, and compliance aspects of this topic, but not with instructions that would enable harmful biological activity."

    return "Here is the answer based on the information currently available."

def compose_response_plan(
    frame: TaskFrame,
    decisions: List[DecisionNode],
    verification: VerificationResult,
    *,
    direct_answer_hint: Optional[str]=None,
    educational_points: Optional[List[str]]=None,
    recommended_next_steps: Optional[List[str]]=None,
    source_refs: Optional[List[str]]=None,
    product_help: bool=False,
    document_review: bool=False,
    form_e: bool=False,
    safety_redirect: bool=False,
) -> ResponsePlan:
    if verification.decision == "FAIL":
        raise ResponseCompositionError(
            "cannot compose user-facing response from failed semantic verification"
        )

    rtype=choose_response_type(
        frame,decisions,verification,
        product_help=product_help,
        document_review=document_review,
        form_e=form_e,
        safety_redirect=safety_redirect,
    )

    direct=_default_direct_answer(rtype,decisions,direct_answer_hint)

    clarifications=[]
    if rtype == ResponseType.NEEDS_CLARIFICATION:
        clarifications=_clarifications_from_decisions(decisions)

    why=_dedupe((educational_points or []) + _why_this_matters(decisions))
    next_steps=_dedupe(recommended_next_steps or [])

    # Avoid duplicating clarification questions as "next steps".
    clarification_keys={" ".join(x.lower().split()) for x in clarifications}
    next_steps=[x for x in next_steps if " ".join(x.lower().split()) not in clarification_keys]

    # Product help and safety redirects should not surface regulatory evidence.
    refs=[] if rtype in {ResponseType.PRODUCT_HELP,ResponseType.SAFETY_REDIRECT} else _dedupe(source_refs or [])

    return ResponsePlan(
        response_type=rtype,
        direct_answer=direct,
        why_this_matters=why,
        clarification_questions=clarifications,
        recommended_next_steps=next_steps,
        source_refs=refs,
        show_sources_collapsed=bool(refs),
    )

def render_response(plan: ResponsePlan) -> Dict[str,Any]:
    # Structured rendering for the web shell.
    # Sections appear only when they contain useful content.
    out={
        "response_type": plan.response_type.value,
        "direct_answer": plan.direct_answer,
        "sections": []
    }

    if plan.why_this_matters:
        out["sections"].append({
            "key":"why_this_matters",
            "title":"Why this matters",
            "items":plan.why_this_matters
        })

    if plan.clarification_questions:
        out["sections"].append({
            "key":"what_i_need",
            "title":"What I need from you",
            "items":plan.clarification_questions
        })

    if plan.recommended_next_steps:
        out["sections"].append({
            "key":"recommended_next_step",
            "title":"What to do next",
            "items":plan.recommended_next_steps
        })

    if plan.source_refs:
        out["sections"].append({
            "key":"sources",
            "title":"Sources & evidence",
            "items":plan.source_refs,
            "collapsed":True
        })

    return out
