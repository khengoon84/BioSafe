
from __future__ import annotations
from pathlib import Path
import sys

ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT/"src", ROOT/"unified_v1"/"src"):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from biosafe_unified221 import EvidenceRequirementPlanner
from biosafe_unified22.service import BioSafeConstitutionAwareInferenceServiceV01

class Unified221Service:
    def __init__(self):
        self.planner=EvidenceRequirementPlanner()
        self.engine=BioSafeConstitutionAwareInferenceServiceV01(ROOT)

    def plan(self, prep):
        return self.planner.plan(
            prep["intent"], prep["query"],
            attachments_present=bool(prep.get("attachments")),
            case_state=prep.get("case_state") or {}
        )

    def direct_no_rag(self, prep):
        q=prep["query"].strip().lower()
        intent=prep["intent"]

        if intent=="product_help":
            if q in {"who are you","what can you do"}:
                return {
                    "direct_answer":"I’m BioSafe, an evidence-grounded biosafety and biosecurity assistant for researchers. I can explain biosafety concepts, help assess regulatory questions, review biosafety-related documents, and assist with researcher-facing Form E preparation.",
                    "limitations":["I provide decision support and do not grant regulatory approval or certify compliance."]
                }
            if q in {"do you know who i am","do u know who i am","do you know me","do u know me"}:
                return {
                    "direct_answer":"I only know information you’ve shared with me in this BioSafe conversation or project context. I don’t independently know your identity."
                }

        # No generic regulatory fallback. If a simple question is not covered by
        # deterministic product behavior, constitution-aware generation may be
        # used later without regulatory retrieval in v0.2.
        return None

    def infer_with_plan(self, prep):
        plan=self.plan(prep)
        direct=self.direct_no_rag(prep)
        if direct is not None:
            direct["_evidence_plan"]=plan.__dict__
            return direct

        # v0.1 preserves the validated frozen generation path for evidence-requiring
        # tasks. The plan is attached internally for audit and later source filtering.
        result=self.engine.infer(
            prep["query"],
            documents=[],
            workflow={"review":"document_review","form-e":"form_e"}.get(prep["workflow"],"ask"),
            interaction_context={
                "intent":prep["intent"],
                "case_state":prep["case_state"],
                "resolved_reference":prep["resolved_reference"],
                "attachments_present":bool(prep["attachments"]),
                "evidence_plan":plan.__dict__,
            }
        )
        if isinstance(result,dict):
            result["_evidence_plan"]=plan.__dict__
        return result
