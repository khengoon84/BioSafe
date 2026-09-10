
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
from context_budget_manager_v0_1 import (
    select_profile, budget_evidence, compact_packet_for_budget, response_contract
)
from deterministic_response_assembler_v0_1 import assemble_biosafe_response
from output_normalizer_v0_3_2 import normalize_output
from policy_shell_enforcer_v0_3_2 import enforce_policy_shell
from output_validator_v0_2 import validate_output
from boundary_validator_v0_3_2 import validate_boundaries
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV011
from response_budget_guard_v0_1 import enforce_response_budget
from document_decision_guard_v0_1 import apply_document_decision_guard
from document_evidence_alias_normalizer_v0_1 import normalize_document_evidence_aliases
from document_fact_precedence_guard_v0_1 import enforce_document_fact_precedence
from structured_document_benchmark_adapter_v0_1 import BioSafeStructuredBenchmarkAdapterV01
from user_document_evidence_adapter_v0_1 import merge_document_evidence_into_bundle
from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"


def _policy_dict(decision):
    if hasattr(decision, "to_dict"):
        return decision.to_dict()
    return {
        "short_circuit": getattr(decision, "short_circuit", False),
        "mode": getattr(decision, "mode", "NORMAL"),
        "constraints": getattr(decision, "constraints", []),
        "reason": getattr(decision, "reason", ""),
        "matched_rules": getattr(decision, "matched_rules", []),
        "deterministic_response": getattr(decision, "deterministic_response", None),
    }


def _unpack_pipeline_messages(result):
    items = list(result) if isinstance(result, (tuple, list)) else [result]
    bundle = None
    messages = None
    extras = []
    for item in items:
        if isinstance(item, dict) and bundle is None and (
            "evidence_bundle" in item or "route" in item or "user_query" in item
        ):
            bundle = item
            continue
        if isinstance(item, list) and messages is None:
            if all(isinstance(x, dict) and "role" in x and "content" in x for x in item):
                messages = item
                continue
        extras.append(item)
    if bundle is None or messages is None:
        raise RuntimeError("Could not identify BioSafe pipeline bundle/messages.")
    return bundle, messages, extras


def _compact_messages(base_messages, query, bundle, packet, policy, profile, workflow):
    system = base_messages[0]["content"] if base_messages else "You are BioSafe."
    evidence, _ = budget_evidence(bundle.get("evidence_bundle", []), profile)
    compact_packet = compact_packet_for_budget(packet, profile) if packet else {}
    payload = {
        "task": "Provide compact BioSafe reasoning using only supplied evidence, document findings and policy constraints.",
        "user_query": query,
        "workflow": workflow,
        "policy": policy,
        "policy_instruction": (
            f"Policy mode: {policy.get('mode','NORMAL')}. Constraints: "
            + "; ".join(policy.get("constraints", []))
        ),
        "route": bundle.get("route", {}),
        "evidence_bundle": evidence,
        "structured_document_findings": compact_packet,
        "response_contract": response_contract(profile),
        "required_output_fields": [
            "conclusion",
            "missing_information",
            "recommended_next_step",
        ],
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def _ollama(model, messages, num_predict):
    body = json.dumps({
        "model": model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_predict": int(num_predict)},
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=body, headers={"Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req, timeout=900) as r:
        payload = json.loads(r.read().decode("utf-8"))
    raw = ((payload.get("message") or {}).get("content") or "").strip()
    try:
        compact = json.loads(raw)
        valid = isinstance(compact, dict)
    except Exception:
        compact = None
        valid = False
    if not valid:
        compact = {
            "conclusion": "The compact model response could not be reliably parsed.",
            "missing_information": [],
            "recommended_next_step": ["Review the case through the BioSafe validation pathway."],
        }
    return compact, valid, payload


class BioSafeFullInferenceServiceV011:
    def __init__(self, project_root: str | Path = ROOT):
        self.root = Path(project_root)
        self.pipeline = BioSafePipelineV032(root=self.root, top_k=3)
        self.reg_guard = RegulatoryLanguageGuardV011()
        self.doc_adapter = BioSafeStructuredBenchmarkAdapterV01(self.root)
        self.router = ComplexityEscalationRouterV01()

    def _restricted_response(self, safety):
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

    def infer(self, query: str, documents: list[dict] | None = None, workflow: str = "ask"):
        documents = documents or []
        hard_safety = classify_safety(query)
        if getattr(hard_safety, "restricted", False):
            return self._restricted_response(hard_safety)

        pd = _policy_dict(classify_policy(query))
        bundle, base_messages, _ = _unpack_pipeline_messages(
            self.pipeline.build_messages(query, safety_class=None)
        )

        packet = {}
        if documents:
            analysed = []
            for i, d in enumerate(documents):
                fn = d.get("filename") or f"SOP-01-upload-{i+1}.txt"
                analysed.append(self.doc_adapter.analyse(fn, d.get("text") or ""))
            packet = self.doc_adapter.build_packet(
                query, analysed, bundle.get("evidence_bundle", []), pd.get("mode", "NORMAL")
            )
            bundle = merge_document_evidence_into_bundle(bundle, packet, max_items=6)

        routing_packet = packet if packet else {
            "documents": documents,
            "missing_fields": [],
            "contradictions": [],
        }
        route_decision = self.router.route(routing_packet)
        model = route_decision["model"]
        profile = select_profile(model)

        messages = _compact_messages(
            base_messages, query, bundle, packet, pd, profile, workflow
        )
        compact, valid, ollama_meta = _ollama(
            model, messages, getattr(profile, "output_token_budget", 420)
        )

        final = assemble_biosafe_response(
            compact, bundle,
            max_missing=getattr(profile, "max_missing_findings", 3),
            max_recommendations=getattr(profile, "max_recommendations", 2),
            max_evidence=getattr(profile, "max_rag_claims", 3),
            max_limitations=getattr(profile, "max_limitations", 1),
        )

        if packet:
            final, _ = normalize_document_evidence_aliases(
                final, bundle.get("evidence_bundle", [])
            )
            final, _ = enforce_document_fact_precedence(final, packet)
            final, _ = apply_document_decision_guard(final, packet)

        final, _ = normalize_output(final)
        final, _ = enforce_policy_shell(final, pd)
        final, _ = self.reg_guard.apply(final, bundle.get("evidence_bundle", []))

        budget_result = enforce_response_budget(
            final,
            max_missing=getattr(profile, "max_missing_findings", 3),
            max_recommendations=getattr(profile, "max_recommendations", 2),
            max_limitations=getattr(profile, "max_limitations", 1),
            max_evidence=getattr(profile, "max_rag_claims", 3),
        )
        final = budget_result[0] if isinstance(budget_result, tuple) else budget_result

        ov = validate_output(final, bundle, valid_json=valid)
        bv = validate_boundaries(final, pd)
        final["_meta"] = {
            "workflow": workflow,
            "model": model,
            "model_called": True,
            "valid_json_first_pass": valid,
            "done_reason": ollama_meta.get("done_reason"),
            "route_reasons": route_decision.get("reasons", []),
            "policy_mode": pd.get("mode", "NORMAL"),
            "output_validation": ov.to_dict() if hasattr(ov, "to_dict") else str(ov),
            "boundary_validation": bv.to_dict() if hasattr(bv, "to_dict") else str(bv),
            "document_count": len(documents),
        }
        return final

# Backward-compatible name used by Stage 9 service.py
BioSafeFullInferenceServiceV01 = BioSafeFullInferenceServiceV011
