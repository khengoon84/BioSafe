from __future__ import annotations
from typing import Any, Dict, List, Optional

from cra_service_runtime_v0_1 import CRAServiceRuntimeV01
from followup_continuity_guard_v0_1 import apply_followup_continuity
from integration_quality_guard_v0_1 import enforce_output_domain_and_recommendation_grounding

class CRAServiceRuntimeV011(CRAServiceRuntimeV01):
    """
    CRA-8.3.1 quality-corrected runtime.

    It preserves CRA-8.2 routing and the frozen inference service but adds:
    1) generalized referential-follow-up continuity before task framing;
    2) post-response output-domain enforcement;
    3) recommendation grounding.
    """
    def handle(self,query,*,workflow="ask",documents=None,session_id=None):
        # We intentionally reproduce the CRA-8.2 orchestration sequence so the
        # continuity repair occurs before task framing.
        from cra_contracts_v0_1 import InteractionType
        from interaction_state_engine_v0_1 import process_turn
        from task_frame_builder_v0_1 import build_task_frame
        from evidence_requirement_planner_v0_1 import plan_evidence
        from retrieval_request_adapter_v0_1 import build_retrieval_request
        from cra_service_runtime_v0_1 import _force_workflow_domain, _local_response, product_help_answer

        q=(query or "").strip()
        if not q:
            raise ValueError("query is required")
        if workflow not in {"ask","review","form-e"}:
            raise ValueError(f"unsupported workflow: {workflow}")

        ctx=self.sessions.get_or_create(session_id)
        ctx.turn_number+=1
        turn_id=f"{ctx.session_id}-t{ctx.turn_number}"

        turn=process_turn(q,turn_id,ctx.conversation,ctx.case)

        interaction, repaired_ref, inherited_domains, continuity_changed = apply_followup_continuity(
            q,turn.interaction,turn.conversation_state,turn.case_state,turn.resolved_reference
        )
        turn.interaction=interaction
        turn.resolved_reference=repaired_ref

        # If this is a referential follow-up, preserve the already-established
        # active task domains rather than letting a short question erase them.
        if continuity_changed and inherited_domains:
            turn.case_state.active_domains=list(inherited_domains)

        ctx.conversation=turn.conversation_state
        ctx.case=turn.case_state

        frame=build_task_frame(
            q,turn.interaction,ctx.case,
            resolved_reference=turn.resolved_reference,
            task_id=turn_id
        )

        if continuity_changed and inherited_domains and not frame.activated_domains:
            frame.activated_domains=list(inherited_domains)
            frame.inactive_domains=[d for d in frame.inactive_domains if d not in inherited_domains]

        frame=_force_workflow_domain(frame,workflow)
        ctx.case.active_domains=list(frame.activated_domains)
        ctx.case.inactive_domains=list(frame.inactive_domains)

        evidence_plan=plan_evidence(frame)
        retrieval=build_retrieval_request(frame,evidence_plan)
        interaction_type=turn.interaction.interaction_type

        if interaction_type==InteractionType.PRODUCT_HELP and workflow=="ask":
            response=_local_response("product_help",product_help_answer(q))
            route="product_help_bypass"
        elif interaction_type==InteractionType.SOCIAL and workflow=="ask":
            response=_local_response("simple_answer","Hello. How can I help with your biosafety or biosecurity work?")
            route="social_bypass"
        elif evidence_plan.skip_rag and interaction_type==InteractionType.FOLLOW_UP and inherited_domains:
            # Important: a referential explanatory follow-up in an established
            # domain should still use the authoritative domain path.
            evidence_plan.skip_rag=False
            evidence_plan.required_domains=list(inherited_domains)
            retrieval=build_retrieval_request(frame,evidence_plan)
            result=self.adapter.run(frame,evidence_plan,retrieval,documents=list(documents or []),workflow=workflow)
            response=dict(result.response)
            response["_cra_adapter"]=result.adapter_meta
            route="frozen_domain_adapter"
        elif evidence_plan.skip_rag:
            response=_local_response(
                "simple_answer",
                "I can continue from the previous context, but this turn does not require a new regulatory retrieval."
            )
            route="conversation_local"
        else:
            result=self.adapter.run(frame,evidence_plan,retrieval,documents=list(documents or []),workflow=workflow)
            response=dict(result.response)
            response["_cra_adapter"]=result.adapter_meta
            route="frozen_domain_adapter"

        if route=="frozen_domain_adapter":
            response,qmeta=enforce_output_domain_and_recommendation_grounding(
                response,
                active_domains=frame.activated_domains,
                excluded_domains=evidence_plan.exclude_domains,
            )
            response["_cra_quality"]=qmeta
        else:
            qmeta={"removed_count":0,"removed":[]}

        ctx.last_response=response
        return {
            "session_id":ctx.session_id,
            "turn_id":turn_id,
            "workflow":workflow,
            "route":route,
            "interaction_type":interaction_type.value,
            "task_frame":{
                "activated_domains":list(frame.activated_domains),
                "inactive_domains":list(frame.inactive_domains),
                "decisions_requested":list(frame.decisions_requested),
            },
            "response":response,
            "_cra_bridge":{
                "version":"CRA-8.3.1-v0.1",
                "session_count":self.sessions.count(),
                "retrieval_skipped":bool(evidence_plan.skip_rag),
                "required_domains":list(evidence_plan.required_domains),
                "excluded_domains":list(evidence_plan.exclude_domains),
                "resolved_reference":turn.resolved_reference,
                "resolved_clarification_field":turn.resolved_clarification_field,
                "continuity_repaired":continuity_changed,
                "inherited_domains":list(inherited_domains),
            }
        }
