
from __future__ import annotations
import json, sys, urllib.request
from pathlib import Path
from typing import Any

ROOT = Path("/home/khengoon/biosafe")
for p in (ROOT, ROOT/"src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from integration_safety_gate_v0_1_2 import classify_safety
from policy_decision_guard_v0_3_3 import classify_policy
from biosafe_pipeline_v0_3_2 import BioSafePipelineV032
from context_budget_manager_v0_1 import select_profile, compact_packet_for_budget
from deterministic_response_assembler_v0_1 import assemble_biosafe_response
from output_normalizer_v0_3_2 import normalize_output
from policy_shell_enforcer_v0_3_2 import enforce_policy_shell
from output_validator_v0_2 import validate_output
from boundary_validator_v0_3_2 import validate_boundaries
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV011

try:
    from response_budget_guard_v0_1 import enforce_response_budget
except Exception:
    enforce_response_budget = None

try:
    from document_decision_guard_v0_1 import apply_document_decision_guard
except Exception:
    apply_document_decision_guard = None

try:
    from document_evidence_alias_normalizer_v0_1 import normalize_document_evidence_aliases
except Exception:
    normalize_document_evidence_aliases = None

try:
    from document_fact_precedence_guard_v0_1 import enforce_document_fact_precedence
except Exception:
    enforce_document_fact_precedence = None

try:
    from structured_document_benchmark_adapter_v0_1 import BioSafeStructuredBenchmarkAdapterV01
except Exception:
    BioSafeStructuredBenchmarkAdapterV01 = None

try:
    from user_document_evidence_adapter_v0_1 import build_user_document_evidence, merge_document_evidence_into_bundle
except Exception:
    build_user_document_evidence = merge_document_evidence_into_bundle = None

try:
    from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01
except Exception:
    ComplexityEscalationRouterV01 = None


def _ollama(model: str, messages: list[dict], num_predict: int = 420) -> tuple[dict, dict]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": num_predict},
    }
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        meta = json.loads(r.read().decode("utf-8"))
    content = ((meta.get("message") or {}).get("content") or "").strip()
    try:
        obj = json.loads(content)
    except Exception:
        obj = {
            "conclusion": "The compact model response could not be reliably parsed.",
            "missing_information": [],
            "recommended_next_step": [],
        }
    return obj, meta


class BioSafeFullInferenceServiceV01:
    """Stage 9 product adapter around the frozen Stage 8 interfaces."""

    def __init__(self, project_root: str | Path = ROOT):
        self.root = Path(project_root)
        self.pipeline = BioSafePipelineV032(root=self.root, top_k=3)
        self.reg_guard = RegulatoryLanguageGuardV011()
        self.doc_adapter = (
            BioSafeStructuredBenchmarkAdapterV01(self.root)
            if BioSafeStructuredBenchmarkAdapterV01 else None
        )
        self.complexity = ComplexityEscalationRouterV01() if ComplexityEscalationRouterV01 else None

    def _restricted_response(self, safety) -> dict:
        return {
            "conclusion": "I can’t provide actionable assistance that increases harmful biological capability or bypasses containment.",
            "applicable_authority": [],
            "evidence": [],
            "missing_information": [],
            "recommended_next_step": [
                "I can help with risk reduction, containment, biosafety controls, or high-level safety information instead."
            ],
            "limitations": [
                "BioSafe does not provide actionable assistance that increases harmful biological capability or defeats containment."
            ],
            "safety": {
                "classification": "refusal",
                "response_mode": "refuse_and_redirect",
                "reason": getattr(safety, "reason", "") or "restricted_biological_capability",
            },
            "_meta": {"route": "deterministic_safety", "model_called": False},
        }

    def infer(self, query: str, documents: list[dict] | None = None, workflow: str = "ask") -> dict:
        documents = documents or []
        safety = classify_safety(query)
        if getattr(safety, "restricted", False):
            return self._restricted_response(safety)

        policy = classify_policy(query)
        built = self.pipeline.build_messages(query=query)
        bundle, messages, *extra = built

        packet = {}
        if documents and self.doc_adapter:
            analysed = []
            for i, d in enumerate(documents):
                filename = d.get("filename") or f"SOP-01-upload-{i+1}.txt"
                text = d.get("text") or ""
                analysed.append(self.doc_adapter.analyse(filename, text))
            rag = bundle.get("evidence_bundle", bundle.get("evidence", [])) if isinstance(bundle, dict) else []
            packet = self.doc_adapter.build_packet(
                query=query, docs=analysed, rag_evidence=rag,
                policy_mode=getattr(policy, "mode", "STANDARD")
            )
            if merge_document_evidence_into_bundle:
                bundle = merge_document_evidence_into_bundle(bundle, packet, max_items=6)

        # Route: primary 0.8B; complex documents/contradictions use 2B.
        model = "qwen3.5:0.8b"
        route_reason = []
        if self.complexity and packet:
            r = self.complexity.route(packet)
            if isinstance(r, dict):
                model = r.get("model") or r.get("model_id") or model
                route_reason = r.get("reasons") or r.get("route_reasons") or []
        elif len(documents) >= 2:
            model = "qwen3.5:2b"
            route_reason = ["multi_document"]

        profile = select_profile(model)

        # Keep compact three-field generation contract.
        compact_instruction = {
            "response_contract": {
                "conclusion": "string, concise advisory conclusion; never certify/approve compliance",
                "missing_information": ["up to 3 strings"],
                "recommended_next_step": ["up to 2 strings"],
            },
            "policy_mode": getattr(policy, "mode", "STANDARD"),
            "policy_constraints": getattr(policy, "constraints", []),
            "workflow": workflow,
        }
        if packet:
            compact_instruction["structured_document_packet"] = compact_packet_for_budget(packet, profile)

        # Patch final user message with product-layer compact contract while retaining frozen messages.
        messages = list(messages)
        messages.append({
            "role": "user",
            "content": json.dumps(compact_instruction, ensure_ascii=False),
        })

        compact, ollama_meta = _ollama(model, messages, num_predict=420)
        final = assemble_biosafe_response(compact, bundle)

        if packet and apply_document_decision_guard:
            final, _ = apply_document_decision_guard(final, packet)
        if packet and normalize_document_evidence_aliases:
            evidence = bundle.get("evidence_bundle", bundle.get("evidence", [])) if isinstance(bundle, dict) else []
            final, _ = normalize_document_evidence_aliases(final, evidence)
        if packet and enforce_document_fact_precedence:
            final, _ = enforce_document_fact_precedence(final, packet)

        final, _ = normalize_output(final)
        final, _ = enforce_policy_shell(final, policy)

        # Regulatory language guard v0.1.1.
        try:
            guarded = self.reg_guard.apply(final)
            if isinstance(guarded, tuple):
                final = guarded[0]
            elif isinstance(guarded, dict):
                final = guarded
        except AttributeError:
            # Alternate validated interface naming.
            try:
                guarded = self.reg_guard.guard(final)
                final = guarded[0] if isinstance(guarded, tuple) else guarded
            except Exception:
                pass

        if enforce_response_budget:
            budgeted = enforce_response_budget(
                final, max_missing=3, max_recommendations=2,
                max_limitations=1, max_evidence=3
            )
            final = budgeted[0] if isinstance(budgeted, tuple) else budgeted

        ov = validate_output(final, bundle, valid_json=True)
        bv = validate_boundaries(final, policy)

        final["_meta"] = {
            "workflow": workflow,
            "model": model,
            "model_called": True,
            "done_reason": ollama_meta.get("done_reason"),
            "route_reasons": route_reason,
            "policy_mode": getattr(policy, "mode", "STANDARD"),
            "output_validation": ov.to_dict() if hasattr(ov, "to_dict") else str(ov),
            "boundary_validation": bv.to_dict() if hasattr(bv, "to_dict") else str(bv),
            "document_count": len(documents),
        }
        return final
