from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from cra_contracts_v0_1 import *
from interaction_state_engine_v0_1 import process_turn
from interaction_manager_v0_1 import classify_interaction
from state_manager_v0_1 import (
    add_pending_clarification, add_assistant_concept, set_domains, update_case_fact
)
from task_frame_builder_v0_1 import build_task_frame
from evidence_requirement_planner_v0_1 import plan_evidence
from retrieval_request_adapter_v0_1 import build_retrieval_request
from dependency_decision_engine_v0_1 import evaluate_decision_readiness, apply_supported_rule
from semantic_verifier_v0_1 import verify_response
from researcher_response_composer_v0_1 import compose_response_plan, render_response

@dataclass
class TrajectoryResult:
    name: str
    family: str
    passed: bool
    assertions_passed: int
    assertions_total: int
    failures: List[str] = field(default_factory=list)

class TrajectoryContext:
    def __init__(self, session_id="s", case_id="c"):
        self.conversation=ConversationState(session_id=session_id)
        self.case=CaseState(case_id=case_id)
        self.turn=0

    def next_turn(self):
        self.turn += 1
        return f"t{self.turn}"

    def process(self,text):
        turn_id=self.next_turn()
        result=process_turn(text,turn_id,self.conversation,self.case)
        self.conversation=result.conversation_state
        self.case=result.case_state
        return result

def pass_verification():
    return VerificationResult(
        decision="PASS",
        checks={
            "prerequisite_sufficiency":True,
            "citation_support":True,
            "jurisdiction_match":True,
            "currentness":True,
            "domain_activation":True,
            "state_consistency":True,
            "unknown_preservation":True,
            "no_certification":True,
            "recommendation_support":True,
            "turn_relevance":True,
        }
    )

def run_trajectory(spec: Dict[str,Any]) -> TrajectoryResult:
    failures=[]
    passed=0
    total=0

    def check(label,cond):
        nonlocal passed,total
        total+=1
        if cond:
            passed+=1
        else:
            failures.append(label)

    ctx=TrajectoryContext(spec["name"],spec["name"])
    setup=spec.get("setup",{})
    if setup.get("jurisdiction"):
        ctx.case.jurisdiction=FactValue(
            value=setup["jurisdiction"],
            status=FactStatus.USER_CONFIRMED,
            source="benchmark",
            confidence=1.0
        )
    for name,val in setup.get("facts",{}).items():
        status=FactStatus(val.get("status","user_confirmed"))
        ctx.case.facts[name]=FactValue(
            value=val.get("value"),
            status=status,
            source="benchmark",
            confidence=1.0 if status==FactStatus.USER_CONFIRMED else None
        )
    ctx.case.active_domains=list(setup.get("active_domains",[]))
    ctx.case.inactive_domains=list(setup.get("inactive_domains",[]))
    ctx.case.open_questions=list(setup.get("open_questions",[]))

    for step in spec["steps"]:
        action=step["action"]

        if action=="add_pending":
            add_pending_clarification(ctx.conversation,step["field"],step["question"],ctx.next_turn())
            continue

        if action=="add_concept":
            add_assistant_concept(ctx.conversation,step["concept_id"],step["label"],ctx.next_turn())
            continue

        if action=="set_domains":
            set_domains(ctx.case,activate=step.get("activate",[]),deactivate=step.get("deactivate",[]))
            continue

        if action=="process":
            result=ctx.process(step["text"])
            exp=step.get("expect",{})
            if "interaction" in exp:
                check(step.get("label","interaction"),result.interaction.interaction_type.value==exp["interaction"])
            if "resolved_reference" in exp:
                check(step.get("label","reference"),result.resolved_reference==exp["resolved_reference"])
            if "resolved_field" in exp:
                check(step.get("label","clarification"),result.resolved_clarification_field==exp["resolved_field"])
            if "fact" in exp:
                name=exp["fact"]["name"]
                f=ctx.case.facts.get(name)
                check(step.get("label","fact"),
                      f is not None and f.value==exp["fact"].get("value") and f.status.value==exp["fact"].get("status"))
            if "pipeline" in exp:
                check(step.get("label","pipeline"),result.interaction.needs_domain_pipeline==exp["pipeline"])

            frame=build_task_frame(
                step["text"],result.interaction,ctx.case,
                resolved_reference=result.resolved_reference
            )
            plan=plan_evidence(frame)

            if "activated_domains" in exp:
                check(step.get("label","domains"),sorted(frame.activated_domains)==sorted(exp["activated_domains"]))
            if "skip_rag" in exp:
                check(step.get("label","rag"),plan.skip_rag==exp["skip_rag"])
            if "excluded_contains" in exp:
                check(step.get("label","exclusion"),
                      all(x in plan.exclude_domains for x in exp["excluded_contains"]))
            continue

        if action=="decision_readiness":
            d=evaluate_decision_readiness(
                step["decision_type"],ctx.case,specific=step.get("specific",False)
            )
            exp=step["expect"]
            if "status" in exp:
                check(step.get("label","decision status"),d.status.value==exp["status"])
            if "unresolved_contains" in exp:
                check(step.get("label","unresolved"),
                      all(x in d.unresolved_dependencies for x in exp["unresolved_contains"]))
            continue

        if action=="verify":
            decisions=[]
            for dspec in step.get("decisions",[]):
                prereqs=[PrerequisiteResult(x["name"],x["satisfied"],x.get("fact_refs",[]))
                         for x in dspec.get("prerequisites",[])]
                decisions.append(DecisionNode(
                    decision_id=dspec["decision_id"],
                    decision_type=dspec["decision_type"],
                    status=DecisionStatus(dspec["status"]),
                    prerequisites=prereqs,
                    authority_refs=dspec.get("authority_refs",[]),
                    evidence_ids=dspec.get("evidence_ids",[]),
                    unresolved_dependencies=dspec.get("unresolved_dependencies",[]),
                    reason=dspec.get("reason","")
                ))
            frame=TaskFrame(
                task_id="verify",
                interaction_type=InteractionType(step.get("interaction_type","NEW_TASK")),
                user_goal="benchmark",
                current_question=step.get("question","q"),
                jurisdiction=step.get("jurisdiction",ctx.case.jurisdiction.value),
                activated_domains=step.get("activated_domains",ctx.case.active_domains),
                inactive_domains=step.get("inactive_domains",ctx.case.inactive_domains),
                response_expectations=step.get("response_expectations",[])
            )
            vr=verify_response(
                frame,ctx.case,decisions,step.get("payload",{}),step.get("evidence_catalog",{})
            )
            check(step.get("label","verification"),vr.decision==step["expect"]["decision"])
            for key,val in step["expect"].get("checks",{}).items():
                check(step.get("label",key),vr.checks.get(key)==val)
            continue

        if action=="compose":
            frame=TaskFrame(
                task_id="compose",
                interaction_type=InteractionType(step.get("interaction_type","NEW_TASK")),
                user_goal="benchmark",
                current_question="q",
                jurisdiction=ctx.case.jurisdiction.value,
                activated_domains=step.get("activated_domains",[])
            )
            decisions=[]
            for dspec in step.get("decisions",[]):
                decisions.append(DecisionNode(
                    decision_id=dspec["decision_id"],
                    decision_type=dspec["decision_type"],
                    status=DecisionStatus(dspec["status"]),
                    unresolved_dependencies=dspec.get("unresolved_dependencies",[]),
                    reason=dspec.get("reason","")
                ))
            plan=compose_response_plan(
                frame,decisions,pass_verification(),
                direct_answer_hint=step.get("direct_answer_hint"),
                educational_points=step.get("educational_points"),
                recommended_next_steps=step.get("recommended_next_steps"),
                source_refs=step.get("source_refs"),
                product_help=step.get("product_help",False),
                document_review=step.get("document_review",False),
                form_e=step.get("form_e",False),
                safety_redirect=step.get("safety_redirect",False),
            )
            rendered=render_response(plan)
            exp=step["expect"]
            if "response_type" in exp:
                check(step.get("label","response type"),rendered["response_type"]==exp["response_type"])
            if "section_keys" in exp:
                keys=[x["key"] for x in rendered["sections"]]
                check(step.get("label","sections"),keys==exp["section_keys"])
            if "source_refs_empty" in exp:
                check(step.get("label","source refs"),(plan.source_refs==[])==exp["source_refs_empty"])
            continue

    return TrajectoryResult(
        name=spec["name"],
        family=spec["family"],
        passed=(passed==total),
        assertions_passed=passed,
        assertions_total=total,
        failures=failures
    )
