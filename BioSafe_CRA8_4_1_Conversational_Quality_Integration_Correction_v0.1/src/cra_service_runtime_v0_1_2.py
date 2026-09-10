from __future__ import annotations
from cra_service_runtime_v0_1_1 import CRAServiceRuntimeV011
from conversational_quality_v0_1 import (CONCEPT_CARDS,normalize_likely_entity,detect_foundational_intent,detect_entity_card,is_elaboration_request,elaborate_previous_response,sanitize_user_response)

class CRAServiceRuntimeV012(CRAServiceRuntimeV011):
    """CRA-8.4.1 conversational-quality correction. Frozen inference/RAG is not modified."""
    def handle(self,query,*,workflow="ask",documents=None,session_id=None):
        raw=(query or "").strip()
        if not raw: raise ValueError("query is required")
        normalized,entity=normalize_likely_entity(raw)

        # Stable foundational educational concepts: deterministic, authoritative and uncluttered.
        if workflow=="ask":
            key=detect_foundational_intent(normalized) or detect_entity_card(normalized)
            if key:
                ctx=self.sessions.get_or_create(session_id); ctx.turn_number+=1
                turn_id=f"{ctx.session_id}-t{ctx.turn_number}"
                response=dict(CONCEPT_CARDS[key])
                ctx.last_response=response
                return {"session_id":ctx.session_id,"turn_id":turn_id,"workflow":workflow,"route":"authoritative_concept_card","interaction_type":"NEW_TASK","task_frame":{"activated_domains":["general_biosafety"],"inactive_domains":[],"decisions_requested":["educational_explanation"]},"response":response,"_cra_bridge":{"version":"CRA-8.4.1-v0.1","retrieval_skipped":True,"entity_normalized_to":entity,"quality_correction":"authoritative_educational_grounding"}}

            # Pure elaboration should use the previous supported answer; never expose routing prose.
            if is_elaboration_request(raw):
                ctx=self.sessions.get_or_create(session_id)
                prior=elaborate_previous_response(getattr(ctx,"last_response",{}) or {})
                if prior:
                    ctx.turn_number+=1; turn_id=f"{ctx.session_id}-t{ctx.turn_number}"; ctx.last_response=prior
                    return {"session_id":ctx.session_id,"turn_id":turn_id,"workflow":workflow,"route":"supported_elaboration","interaction_type":"REFORMULATE","task_frame":{"activated_domains":list(getattr(ctx.case,"active_domains",[]) or []),"inactive_domains":[],"decisions_requested":["elaborate_previous_answer"]},"response":prior,"_cra_bridge":{"version":"CRA-8.4.1-v0.1","retrieval_skipped":True,"quality_correction":"supported_followup_elaboration"}}

        out=super().handle(normalized,workflow=workflow,documents=documents,session_id=session_id)
        rtype=(out.get("response") or {}).get("response_type")
        out["response"]=sanitize_user_response(out.get("response") or {},response_type=rtype)
        out.setdefault("_cra_bridge",{})["version"]="CRA-8.4.1-v0.1"
        if entity: out["_cra_bridge"]["entity_normalized_to"]=entity
        return out
