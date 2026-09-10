from pathlib import Path
import sys

ROOT = Path("/home/khengoon/biosafe")
for path in (ROOT / "src", ROOT / "unified_v1/src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import full_inference_service_v0_1 as frozen
from biosafe_unified221 import EvidenceRequirementPlanner
from biosafe_unified22 import load_constitution, augment_compact_messages
from biosafe_unified222 import normalize_intent
from biosafe_unified223 import ScopedPipelineAdapter
from biosafe_unified224 import ResponseTypeContractEnforcer
from biosafe_unified2241 import EvidencePreservingSemanticVerifier
from biosafe_unified2242 import SubjectAwareEvidenceScopeEnforcer
from biosafe_unified225 import RequestedSubjectCoverageGuard, SafetyRationaleGuard
from biosafe_unified2251.guards import DecisionSemanticsGuard, vetted_direct_answer
from biosafe_unified226 import (
    parse_act,
    load_concept_table,
    render_concept_answer,
    DETERMINISTIC_EDUCATIONAL_CONCEPTS,
)
from biosafe_unified226.vision_inference import (
    run_vision_inference,
    is_image_document,
)


class Unified2251Service:
    def __init__(self):
        self.planner = EvidenceRequirementPlanner()
        self.scope = SubjectAwareEvidenceScopeEnforcer()
        self.constitution = load_constitution()
        self.engine = frozen.BioSafeFullInferenceServiceV011(ROOT)
        self.contract = ResponseTypeContractEnforcer()
        self.semantic = EvidencePreservingSemanticVerifier()
        self.decision = DecisionSemanticsGuard()
        self.coverage = RequestedSubjectCoverageGuard()
        self.safety_rationale = SafetyRationaleGuard()
        self.concept_table = load_concept_table()

    def intent(self, prep):
        upstream = normalize_intent(prep["query"], prep.get("intent"))
        # Social/deterministic acts recognized structurally take priority so the
        # model is not needed for greetings, product help, or self-knowledge turns.
        act = parse_act(prep["query"]).get("act")
        if act in ("greeting", "product_help", "self_knowledge") and upstream in (
            "simple_answer", "educational_answer", "follow_up", None,
        ):
            return act
        return upstream

    def plan(self, prep):
        intent = self.intent(prep)
        if intent == "self_knowledge":
            intent = "simple_answer"
        return self.planner.plan(
            intent,
            prep["query"],
            attachments_present=bool(prep.get("attachments")),
            case_state=prep.get("case_state") or {},
        )

    def direct(self, prep, intent):
        if intent == "greeting":
            return {
                "direct_answer": (
                    "Hi! I’m BioSafe, your evidence-grounded biosafety and biosecurity assistant. "
                    "I can explain concepts like biosafety, biosecurity, risk groups and containment, "
                    "help you think through regulatory questions, review biosafety documents, or help "
                    "with researcher-facing Form E preparation. What would you like to explore?"
                ),
            }
        if intent == "product_help":
            return {
                "direct_answer": (
                    "Hi there! I’m BioSafe, your evidence-grounded biosafety and biosecurity "
                    "assistant for researchers. Here’s what I can help with:\n\n"
                    "- **Explain concepts**: biosafety, biosecurity, risk groups, BSL, containment, etc.\n"
                    "- **Assess regulatory questions**: help you reason through whether a permit, "
                    "notification, or approval might apply (with the right facts).\n"
                    "- **Review documents**: upload lab protocols, SOPs, or risk assessments and I’ll "
                    "flag biosafety gaps.\n"
                    "- **Form E assistance**: help prepare the researcher-facing portions of Malaysia’s "
                    "Form E for genetic modification projects — but only with your project-specific facts.\n\n"
                    "I provide decision support and do not grant regulatory approval or certify compliance."
                ),
            }
        if intent == "self_knowledge":
            return {
                "direct_answer": (
                    "I only know information you’ve shared with me in this BioSafe conversation or "
                    "project context. I don’t independently know your identity — but I’m happy to help "
                    "with biosafety and biosecurity questions!"
                )
            }
        return None

    def acts(self, prep, documents=None):
        prepared_act = prep.get("conversation_act")
        if isinstance(prepared_act, dict):
            return prepared_act
        documents = documents or []
        return parse_act(
            prep["query"],
            attachments=documents + (prep.get("attachments") or []),
            previous_subject=prep.get("previous_subject"),
            previous_concept=prep.get("previous_concept"),
        )

    def infer(self, prep, documents=None):
        documents = documents or []
        intent = self.intent(prep)
        plan = self.plan(prep)
        act = self.acts(prep, documents)

        # Image uploads: never hand binary/image payloads to the frozen text-only
        # core (which otherwise renames them "SOP-01-upload-N.txt"). Route to the
        # vision-capable model, then vet the output with the existing guards.
        if any(is_image_document(d) for d in documents):
            hard_safety = frozen.classify_safety(prep["query"])
            if getattr(hard_safety, "restricted", False):
                out = self.engine._restricted_response(hard_safety)
                out["_normalized_intent"] = "safety_redirect"
                out["_evidence_plan"] = plan.__dict__
                return out
            out = run_vision_inference(prep["query"], documents, self.constitution)
            out, semantic_audit = self.semantic.apply(out, [])
            out, decision_audit = self.decision.apply(
                out, prep["query"], prep.get("case_state") or {}, []
            )
            out, coverage_audit = self.coverage.apply(out, prep["query"], [])
            out, safety_audit = self.safety_rationale.apply(out, prep["query"])
            # Image observations are educational output for presentation-contract
            # purposes; ``_normalized_intent`` retains the more specific route.
            out, contract_audit = self.contract.apply(out, "educational_answer")
            out["_normalized_intent"] = "image_query"
            out["_evidence_plan"] = plan.__dict__
            out["_semantic_verifier"] = {"audit": semantic_audit, "scoped_evidence_ids": []}
            out["_decision_semantics"] = {"audit": decision_audit}
            out["_subject_coverage"] = {"audit": coverage_audit}
            out["_safety_rationale"] = {"audit": safety_audit}
            out["_response_contract"] = {"intent": "image_query", "audit": contract_audit}
            return out

        direct = self.direct(prep, intent)
        if direct is not None:
            direct["_normalized_intent"] = intent
            direct["_evidence_plan"] = plan.__dict__
            return direct

        # Curated educational concept answers (definition / difference / elaboration).
        if (
            act.get("act") in ("definition", "difference", "elaboration")
            and act.get("concept") in DETERMINISTIC_EDUCATIONAL_CONCEPTS
        ):
            mode = "elaborate" if act.get("act") == "elaboration" else "full"
            concept_out = render_concept_answer(act["concept"], self.concept_table, mode=mode)
            if concept_out is not None:
                concept_out["_normalized_intent"] = act["act"]
                concept_out["_evidence_plan"] = plan.__dict__
                return concept_out

        # Vetted exact-concept sentences for any remaining recognized queries.
        vetted = vetted_direct_answer(prep["query"])
        if vetted is not None:
            vetted["_normalized_intent"] = "educational_answer"
            vetted["_evidence_plan"] = plan.__dict__
            return vetted

        original_pipeline = self.engine.pipeline
        original_compact = frozen._compact_messages
        scoped = ScopedPipelineAdapter(original_pipeline, self.scope, plan, prep["query"])
        captured = {"evidence": []}

        def compact(base, query, bundle, packet, policy, profile, workflow):
            captured["evidence"] = [dict(item) for item in bundle.get("evidence_bundle", [])]
            messages = original_compact(base, query, bundle, packet, policy, profile, workflow)
            return augment_compact_messages(
                messages,
                constitution=self.constitution,
                interaction_context={
                    "intent": intent,
                    "case_state": prep.get("case_state") or {},
                    "resolved_reference": prep.get("resolved_reference"),
                    "attachments_present": bool(prep.get("attachments")),
                    "evidence_plan": plan.__dict__,
                },
            )

        self.engine.pipeline = scoped
        frozen._compact_messages = compact
        try:
            out = self.engine.infer(
                prep["query"],
                documents=documents,
                workflow={"review": "document_review", "form-e": "form_e"}.get(
                    prep["workflow"], "ask"
                ),
            )
        finally:
            self.engine.pipeline = original_pipeline
            frozen._compact_messages = original_compact

        out, semantic_audit = self.semantic.apply(out, captured["evidence"])
        out, decision_audit = self.decision.apply(
            out, prep["query"], prep.get("case_state") or {}, captured["evidence"]
        )
        out, coverage_audit = self.coverage.apply(out, prep["query"], captured["evidence"])
        out, safety_audit = self.safety_rationale.apply(out, prep["query"])
        out, contract_audit = self.contract.apply(out, intent)
        out["_normalized_intent"] = intent
        out["_evidence_plan"] = plan.__dict__
        out["_scope_audit"] = scoped.audit
        out["_semantic_verifier"] = {
            "audit": semantic_audit,
            "scoped_evidence_ids": [item.get("evidence_id") for item in captured["evidence"]],
        }
        out["_decision_semantics"] = {"audit": decision_audit}
        out["_subject_coverage"] = {"audit": coverage_audit}
        out["_safety_rationale"] = {"audit": safety_audit}
        out["_response_contract"] = {"intent": intent, "audit": contract_audit}
        return out
