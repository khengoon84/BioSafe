from pathlib import Path
import sys
ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT/"src",ROOT/"unified_v1/src"):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
import full_inference_service_v0_1 as frozen
from biosafe_unified221 import EvidenceRequirementPlanner
from biosafe_unified22 import load_constitution,augment_compact_messages
from biosafe_unified222 import normalize_intent,EvidenceScopeEnforcer
from biosafe_unified223 import ScopedPipelineAdapter,SemanticClaimVerifier

class Unified223Service:
    def __init__(self):
        self.planner=EvidenceRequirementPlanner(); self.scope=EvidenceScopeEnforcer()
        self.constitution=load_constitution(); self.engine=frozen.BioSafeFullInferenceServiceV011(ROOT)
        self.verifier=SemanticClaimVerifier()
    def intent(self,prep): return normalize_intent(prep["query"],prep.get("intent"))
    def plan(self,prep):
        i=self.intent(prep)
        if i=="self_knowledge": i="simple_answer"
        return self.planner.plan(i,prep["query"],attachments_present=bool(prep.get("attachments")),
                                 case_state=prep.get("case_state") or {})
    def direct(self,prep,i):
        if i=="product_help":
            return {"direct_answer":"I’m BioSafe, an evidence-grounded biosafety and biosecurity assistant for researchers. I can explain biosafety concepts, help assess regulatory questions, review biosafety-related documents, and assist with researcher-facing Form E preparation.",
                    "limitations":["I provide decision support and do not grant regulatory approval or certify compliance."]}
        if i=="self_knowledge":
            return {"direct_answer":"I only know information you’ve shared with me in this BioSafe conversation or project context. I don’t independently know your identity."}
    def infer(self,prep,documents=None):
        documents=documents or []; i=self.intent(prep); plan=self.plan(prep); d=self.direct(prep,i)
        if d is not None:
            d["_evidence_plan"]=plan.__dict__;d["_normalized_intent"]=i;return d
        original_pipeline=self.engine.pipeline; original_compact=frozen._compact_messages
        scoped=ScopedPipelineAdapter(original_pipeline,self.scope,plan,prep["query"])
        def compact(base,q,bundle,packet,policy,profile,workflow):
            m=original_compact(base,q,bundle,packet,policy,profile,workflow)
            return augment_compact_messages(m,constitution=self.constitution,interaction_context={
              "intent":i,"case_state":prep.get("case_state") or {},"resolved_reference":prep.get("resolved_reference"),
              "attachments_present":bool(prep.get("attachments")),"evidence_plan":plan.__dict__})
        self.engine.pipeline=scoped; frozen._compact_messages=compact
        try:
            out=self.engine.infer(prep["query"],documents=documents,
              workflow={"review":"document_review","form-e":"form_e"}.get(prep["workflow"],"ask"))
        finally:
            self.engine.pipeline=original_pipeline; frozen._compact_messages=original_compact
        ev=[{"text":e.get("statement") or e.get("text") or ""} for e in out.get("evidence",[]) if isinstance(e,dict)]
        out,flags=self.verifier.apply(out,ev)
        out["_evidence_plan"]=plan.__dict__;out["_normalized_intent"]=i
        out["_scope_audit"]=scoped.audit;out["_semantic_verifier"]={"unsupported":flags}
        return out
