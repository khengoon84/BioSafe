from __future__ import annotations
import threading, uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from cra_contracts_v0_1 import ConversationState, CaseState, InteractionType
from interaction_state_engine_v0_1 import process_turn
from task_frame_builder_v0_1 import build_task_frame
from evidence_requirement_planner_v0_1 import plan_evidence
from retrieval_request_adapter_v0_1 import build_retrieval_request
from frozen_inference_rag_adapter_v0_1 import FrozenInferenceRAGAdapterV01

@dataclass
class SessionContext:
    session_id: str
    conversation: ConversationState
    case: CaseState
    turn_number: int = 0
    last_response: Optional[Dict[str,Any]] = None

class InMemorySessionStore:
    def __init__(self):
        self._lock=threading.RLock()
        self._sessions={}

    def get_or_create(self,session_id=None):
        with self._lock:
            sid=(session_id or "").strip() or f"session-{uuid.uuid4().hex[:12]}"
            if sid not in self._sessions:
                self._sessions[sid]=SessionContext(
                    session_id=sid,
                    conversation=ConversationState(session_id=sid),
                    case=CaseState(case_id=f"case-{sid}")
                )
            return self._sessions[sid]

    def reset(self,session_id):
        with self._lock:
            return self._sessions.pop(session_id,None) is not None

    def count(self):
        with self._lock:
            return len(self._sessions)

def product_help_answer(text):
    t=(text or "").lower()
    if "who are you" in t or "what are you" in t:
        return "I’m BioSafe, a local biosafety and biosecurity assistant designed to support researchers with biosafety questions, document review, and researcher-facing Form E assistance."
    if "document" in t or "review" in t:
        return "I can review biosafety-related SOPs, research proposals, protocols, risk-assessment material, and researcher-facing Form E drafts for gaps, missing information, and internal consistency."
    if "form e" in t:
        return "The Form E Assistant helps map information you provide into the researcher-facing Form E workflow, identifies missing information, and checks consistency. It does not simulate IBC approval or regulatory approval."
    return "I can help with biosafety and biosecurity questions, document review, risk-assessment support, and researcher-facing Form E assistance."

def _force_workflow_domain(frame,workflow):
    forced=None
    if workflow=="review":
        forced="document_review"
    elif workflow=="form-e":
        forced="form_e"
    if forced and forced not in frame.activated_domains:
        frame.activated_domains=sorted(set(frame.activated_domains+[forced]))
        frame.requested_domains=sorted(set(frame.requested_domains+[forced]))
        frame.inactive_domains=[d for d in frame.inactive_domains if d!=forced]
    return frame

def _local_response(response_type,direct_answer):
    return {"response_type":response_type,"direct_answer":direct_answer,"sections":[]}

class CRAServiceRuntimeV01:
    def __init__(self,adapter=None,session_store=None):
        self.adapter=adapter or FrozenInferenceRAGAdapterV01()
        self.sessions=session_store or InMemorySessionStore()

    def handle(self,query,*,workflow="ask",documents=None,session_id=None):
        q=(query or "").strip()
        if not q:
            raise ValueError("query is required")
        if workflow not in {"ask","review","form-e"}:
            raise ValueError(f"unsupported workflow: {workflow}")

        ctx=self.sessions.get_or_create(session_id)
        ctx.turn_number+=1
        turn_id=f"{ctx.session_id}-t{ctx.turn_number}"

        turn=process_turn(q,turn_id,ctx.conversation,ctx.case)
        ctx.conversation=turn.conversation_state
        ctx.case=turn.case_state

        frame=build_task_frame(
            q,turn.interaction,ctx.case,
            resolved_reference=turn.resolved_reference,
            task_id=turn_id
        )
        frame=_force_workflow_domain(frame,workflow)
        ctx.case.active_domains=list(frame.activated_domains)
        ctx.case.inactive_domains=list(frame.inactive_domains)

        evidence_plan=plan_evidence(frame)
        retrieval=build_retrieval_request(frame,evidence_plan)
        interaction=turn.interaction.interaction_type

        if interaction==InteractionType.PRODUCT_HELP and workflow=="ask":
            response=_local_response("product_help",product_help_answer(q))
            route="product_help_bypass"
        elif interaction==InteractionType.SOCIAL and workflow=="ask":
            response=_local_response("simple_answer","Hello. How can I help with your biosafety or biosecurity work?")
            route="social_bypass"
        elif evidence_plan.skip_rag:
            response=_local_response(
                "simple_answer",
                "I can continue from the previous context, but this turn does not require a new regulatory retrieval."
            )
            route="conversation_local"
        else:
            result=self.adapter.run(
                frame,evidence_plan,retrieval,
                documents=list(documents or []),
                workflow=workflow
            )
            response=dict(result.response)
            response["_cra_adapter"]=result.adapter_meta
            route="frozen_domain_adapter"

        ctx.last_response=response
        return {
            "session_id":ctx.session_id,
            "turn_id":turn_id,
            "workflow":workflow,
            "route":route,
            "interaction_type":interaction.value,
            "task_frame":{
                "activated_domains":list(frame.activated_domains),
                "inactive_domains":list(frame.inactive_domains),
                "decisions_requested":list(frame.decisions_requested)
            },
            "response":response,
            "_cra_bridge":{
                "version":"CRA-8.2-v0.1",
                "session_count":self.sessions.count(),
                "retrieval_skipped":bool(evidence_plan.skip_rag),
                "required_domains":list(evidence_plan.required_domains),
                "excluded_domains":list(evidence_plan.exclude_domains),
                "resolved_reference":turn.resolved_reference,
                "resolved_clarification_field":turn.resolved_clarification_field
            }
        }
