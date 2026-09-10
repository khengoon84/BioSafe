
from __future__ import annotations
from pathlib import Path
import sys
ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT/"src",ROOT/"unified_v1"/"src"):
    if str(p) not in sys.path:sys.path.insert(0,str(p))

import full_inference_service_v0_1 as frozen
from biosafe_unified221 import EvidenceRequirementPlanner
from biosafe_unified22 import load_constitution,augment_compact_messages
from biosafe_unified222 import normalize_intent,EvidenceScopeEnforcer

class Unified222Service:
    def __init__(self):
        self.planner=EvidenceRequirementPlanner()
        self.scope=EvidenceScopeEnforcer()
        self.constitution=load_constitution()
        self.engine=frozen.BioSafeFullInferenceServiceV011(ROOT)

    def normalized_intent(self,prep):
        return normalize_intent(prep["query"],prep.get("intent"))

    def plan(self,prep):
        intent=self.normalized_intent(prep)
        if intent=="self_knowledge":
            return self.planner.plan("simple_answer",prep["query"],
                attachments_present=bool(prep.get("attachments")),
                case_state=prep.get("case_state") or {})
        return self.planner.plan(intent,prep["query"],
            attachments_present=bool(prep.get("attachments")),
            case_state=prep.get("case_state") or {})

    def deterministic(self,prep,intent):
        if intent=="product_help":
            return {
              "direct_answer":"I’m BioSafe, an evidence-grounded biosafety and biosecurity assistant for researchers. I can explain biosafety concepts, help assess regulatory questions, review biosafety-related documents, and assist with researcher-facing Form E preparation.",
              "limitations":["I provide decision support and do not grant regulatory approval or certify compliance."]
            }
        if intent=="self_knowledge":
            return {"direct_answer":"I only know information you’ve shared with me in this BioSafe conversation or project context. I don’t independently know your identity."}
        return None

    def infer(self,prep):
        intent=self.normalized_intent(prep)
        plan=self.plan(prep)
        direct=self.deterministic(prep,intent)
        if direct is not None:
            direct["_evidence_plan"]=plan.__dict__
            direct["_normalized_intent"]=intent
            return direct

        original_compact=frozen._compact_messages
        audit={"removed_ids":[],"kept_ids":[]}

        def scoped_compact(base_messages,q,bundle,packet,policy,profile,workflow):
            local=dict(bundle)
            sr=self.scope.apply(bundle.get("evidence_bundle",[]),plan.__dict__,q)
            local["evidence_bundle"]=sr.evidence
            audit["removed_ids"]=[e.get("evidence_id") for e in sr.removed]
            audit["kept_ids"]=[e.get("evidence_id") for e in sr.evidence]
            base=original_compact(base_messages,q,local,packet,policy,profile,workflow)
            return augment_compact_messages(base,constitution=self.constitution,
                interaction_context={
                  "intent":intent,
                  "case_state":prep.get("case_state") or {},
                  "resolved_reference":prep.get("resolved_reference"),
                  "attachments_present":bool(prep.get("attachments")),
                  "evidence_plan":plan.__dict__,
                })

        frozen._compact_messages=scoped_compact
        try:
            result=self.engine.infer(
                prep["query"],documents=[],
                workflow={"review":"document_review","form-e":"form_e"}.get(prep["workflow"],"ask"))
        finally:
            frozen._compact_messages=original_compact

        if isinstance(result,dict):
            result["_evidence_plan"]=plan.__dict__
            result["_normalized_intent"]=intent
            result["_scope_audit"]=audit
        return result
