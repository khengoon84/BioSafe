from __future__ import annotations

import json
import tempfile
from threading import RLock
from pathlib import Path
from typing import Any

ROOT=Path("/home/khengoon/biosafe")
from c5_bridge import build_artifacts, canonical_bytes, retrieval_policy
from candidate_pipeline_v0_1 import CandidatePipelineV01
from phase_c3_7 import C37CFG02
from evidence_aware_subject_coverage_v0_2 import EvidenceAwareSubjectCoverageGuard
from authorization_gate_v0_1 import AuthorizationDecision, evaluate_authorization_decision, decision_summary
from authorization_backstop_v0_1 import FAIL_CLOSED_MESSAGE, apply_authorization_backstop
from authorization_verifier_v0_2 import apply_universal_authorization_verifier


MISSING_FACT_LABELS={
    "jurisdiction":"The country or jurisdiction governing the activity.",
    "material_or_technology_trigger":"The biological material, organism, or technology involved.",
    "specific_activity":"The specific activity, such as contained use, transport, import, export, or disposal.",
}


def augment_candidate_generation_message(message: dict[str,Any]) -> dict[str,Any]:
    """Add the optional, untrusted structured-claim contract to a user message."""
    item=dict(message)
    if item.get("role")!="user":
        return item
    try:
        payload=json.loads(item.get("content") or "{}")
    except (TypeError,ValueError):
        return item
    payload["authorization_claim_contract"]={
        "field":"authorization_claim_candidates",
        "type":"array",
        "required":False,
        "instruction":"Emit only untrusted candidate claims; never infer authority from this field. Omit the field when there is no authorization claim candidate.",
        "item_fields":["kind","concept","polarity","sentence","evidence_ids"],
    }
    response_schema=payload.get("response_schema")
    if isinstance(response_schema,dict):
        schema=json.loads(json.dumps(response_schema))
        properties=dict(schema.get("properties") or {})
        properties["authorization_claim_candidates"]={
            "type":"array",
            "items":{"type":"object","required":["kind","concept","polarity","sentence","evidence_ids"],
                     "properties":{"kind":{"type":"string"},"concept":{"type":["string","null"]},
                                    "polarity":{"type":"string"},"sentence":{"type":"string"},
                                    "evidence_ids":{"type":"array","items":{"type":"string"}}}},
        }
        schema["properties"]=properties
        payload["response_schema"]=schema
    contract=str(payload.get("response_contract") or "")
    payload["response_contract"]=(contract+"\nOptional authorization_claim_candidates is an untrusted candidate list; omit it when empty. It never authorizes a conclusion. Each candidate must include kind, concept, polarity, sentence, and evidence_ids.").strip()
    item["content"]=json.dumps(payload,ensure_ascii=False,indent=2)
    return item


class CandidateInferenceServiceV01:
    """Additive wrapper around the frozen inference service; no frozen file is edited."""

    def __init__(self, root: Path | str = ROOT):
        self.root=Path(root); self._tmp=tempfile.TemporaryDirectory()
        self._inference_lock=RLock()
        self.evaluation_only_serialized_service=True
        directory=Path(self._tmp.name); kb,manifest,_=build_artifacts(); policy=retrieval_policy()
        kp=directory/"candidate_kb.json"; mp=directory/"candidate_manifest.json"; pp=directory/"candidate_policy.json"
        kp.write_bytes(canonical_bytes(kb)); mp.write_bytes(canonical_bytes(manifest)); pp.write_bytes(canonical_bytes(policy))
        self.kb=kb; self.manifest=manifest; self.policy=policy
        self.retriever=C37CFG02(kp,mp,policy_path=pp,metadata_layer=False)
        # Import only the frozen service; replace its pipeline dependency on this instance.
        import sys
        sys.path.insert(0,str(self.root/"unified_v1/src")); sys.path.insert(0,str(self.root/"src"))
        from biosafe_unified2251.service import Unified2251Service
        self.service=Unified2251Service()
        self.service.engine.pipeline=CandidatePipelineV01(self.root,kb,manifest,policy,self.retriever,top_k=3)
        self.service.coverage=EvidenceAwareSubjectCoverageGuard(self.service.coverage)
        original_direct=self.service.direct
        def candidate_direct(prep, intent):
            plan=self.service.plan(prep)
            if not plan.retrieval_required:
                return original_direct(prep, intent)
            return None
        self.service.direct=candidate_direct

    def infer(self, prepared: dict[str,Any], documents: list[dict[str,Any]] | None = None) -> dict[str,Any]:
        with self._inference_lock:
            return self._infer_locked(prepared, documents)

    def _fail_closed_response(self, query: str, auth: AuthorizationDecision, extra_reason_codes: list[str] | None=None) -> dict[str,Any]:
        """Deterministic fail-closed response; never calls the model."""
        missing=list(auth.missing_facts)
        if missing:
            conclusion=("BioSafe cannot determine whether a permit or approval is required for the described "
                        "activity without sufficient project-specific facts and reviewed regulatory evidence.")
        else:
            conclusion=("BioSafe cannot determine whether a permit or approval is required for the described "
                        "activity without reviewed regulatory evidence for this specific case.")
        reason_codes=list(auth.reason_codes)+list(extra_reason_codes or [])
        return {
            "conclusion":conclusion,
            "applicable_authority":[],
            "evidence":[],
            "missing_information":[MISSING_FACT_LABELS[fact] for fact in missing],
            "recommended_next_step":[
                "Provide the country/jurisdiction, the organism/material or technology involved, and a description of the intended activity for a reviewed determination.",
                "Confirm any resulting pathway with the responsible institutional or regulatory authority.",
            ],
            "limitations":["BioSafe has not made a permit, approval, exemption, compliance, or start-work determination."],
            "safety":{
                "status":"FAIL_CLOSED",
                "classification":"caution",
                "response_mode":"ask_before_concluding",
                "reason":"Authorization applicability requires confirmed project facts and adequate authoritative evidence.",
                "reason_codes":reason_codes,
            },
            "authorization_gate":{**decision_summary(auth),"model_called":False},
            "authorization_assessment":{
                "status":"INSUFFICIENT_FACTS" if auth.missing_facts else "INSUFFICIENT_EVIDENCE",
                "renderable":False,
                "reason_codes":list(auth.reason_codes),
                "candidate_count":0,
                "supported_evidence_ids":[],
            },
            "_meta":{
                "candidate_path_id":"C37_METADATA_CFG02:metadata_off",
                "evidence_origin":"C5_REVIEWED_CANDIDATE",
                "frozen_core_modified":False,
                "candidate_inference_bridge":True,
                "model_called":False,
            },
        }

    def _infer_locked(self, prepared: dict[str,Any], documents: list[dict[str,Any]] | None = None) -> dict[str,Any]:
        query=str(prepared.get("query") or "")
        auth=evaluate_authorization_decision(query)
        import full_inference_service_v0_1 as frozen
        import biosafe_unified2251.service as candidate_service_module
        plan=self.service.plan(prepared)
        # Hard fail-closed gate: no model call for high-stakes authorization
        # questions without confirmed facts and an engaged retrieval path.
        if auth.high_stakes and (auth.missing_facts or not plan.retrieval_required):
            extra=["EVIDENCE_UNAVAILABLE"] if (auth.high_stakes and not auth.missing_facts and not plan.retrieval_required) else []
            return self._fail_closed_response(query,auth,extra)
        if hasattr(self.service.coverage,"set_plan"):
            self.service.coverage.set_plan(plan.__dict__)
        original_compact=frozen._compact_messages
        original_assembler=frozen.assemble_biosafe_response
        original_vetted=candidate_service_module.vetted_direct_answer
        original_render=candidate_service_module.render_concept_answer

        def compact_with_candidate(*args, **kwargs):
            messages=original_compact(*args, **kwargs)
            patched=[]
            for message in messages:
                item=dict(message)
                if item.get("role")=="user":
                    try:
                        payload=__import__("json").loads(item["content"])
                        payload["candidate_path_id"]="C37_METADATA_CFG02:metadata_off"
                        payload["evidence_origin"]="C5_REVIEWED_CANDIDATE"
                        item["content"]=__import__("json").dumps(payload,ensure_ascii=False,indent=2)
                        item=augment_candidate_generation_message(item)
                    except (TypeError, ValueError, KeyError):
                        pass
                patched.append(item)
            return patched

        def assemble_with_claim_channel(compact_model_output,*args,**kwargs):
            assembled=original_assembler(compact_model_output,*args,**kwargs)
            if isinstance(assembled,dict) and isinstance(compact_model_output,dict):
                claims=compact_model_output.get("authorization_claim_candidates")
                if claims is not None:
                    assembled["authorization_claim_candidates"]=claims
            return assembled

        frozen._compact_messages=compact_with_candidate if plan.retrieval_required else original_compact
        frozen.assemble_biosafe_response=assemble_with_claim_channel
        candidate_service_module.vetted_direct_answer=(lambda query: None) if plan.retrieval_required else original_vetted
        candidate_service_module.render_concept_answer=(lambda *args, **kwargs: None) if plan.retrieval_required else original_render
        try:
            out=self.service.infer(prepared,documents=documents or [])
        finally:
            frozen._compact_messages=original_compact
            frozen.assemble_biosafe_response=original_assembler
            candidate_service_module.vetted_direct_answer=original_vetted
            candidate_service_module.render_concept_answer=original_render
        if isinstance(out,dict):
            backstop_audit: list[dict[str,Any]]=[]
            # The structured verifier is universal: input intent classification
            # must not be able to bypass the final authorization screen.
            out,verifier_audit=apply_universal_authorization_verifier(
                out, evidence=list(out.get("evidence") or []),
                case_state=prepared.get("case_state") or {},
                structured_claims=out.get("authorization_claim_candidates"))
            if auth.high_stakes:
                out,backstop_audit=apply_authorization_backstop(out)
            meta=dict(out.get("_meta") or {})
            meta.update({"candidate_path_id":"C37_METADATA_CFG02:metadata_off","evidence_origin":"C5_REVIEWED_CANDIDATE","frozen_core_modified":False,"candidate_inference_bridge":True})
            meta["authorization_gate"]=decision_summary(auth)
            if backstop_audit:
                meta.setdefault("authorization_backstop",backstop_audit)
            if verifier_audit:
                meta.setdefault("authorization_verifier",verifier_audit)
            out["_meta"]=meta
        return out

    def close(self):
        self._tmp.cleanup()
