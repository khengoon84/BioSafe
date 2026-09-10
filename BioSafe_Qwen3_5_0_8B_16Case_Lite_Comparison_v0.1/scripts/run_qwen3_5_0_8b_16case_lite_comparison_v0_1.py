#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from biosafe_pipeline_v0_3_2 import BioSafePipelineV032
from output_validator_v0_2 import validate_output
from boundary_validator_v0_3_2 import validate_boundaries
from output_normalizer_v0_3_2 import normalize_output
from policy_shell_enforcer_v0_3_2 import enforce_policy_shell
from run_model_compatibility_v0_1 import check_server, detect_host, model_names
from structured_document_benchmark_adapter_v0_1 import BioSafeStructuredBenchmarkAdapterV01
from document_context_evidence_filter_v0_1 import filter_document_review_evidence, patch_message_evidence
from researcher_ibc_boundary_guard_v0_1 import enforce_researcher_ibc_boundary
from compact_contradiction_renderer_v0_1 import build_compact_contradiction_fallback
from user_document_evidence_adapter_v0_1 import merge_document_evidence_into_bundle
from critical_missing_compliance_guard_v0_1 import enforce_critical_missing_compliance_boundary
from document_evidence_alias_normalizer_v0_1 import normalize_document_evidence_aliases
from document_fact_precedence_guard_v0_1 import enforce_document_fact_precedence
from source_only_draft_renderer_v0_1 import build_source_only_draft_response
from retrieved_claim_semantic_guard_v0_1 import enforce_retrieved_claim_semantic_consistency
from clinical_proposal_semantic_guard_v0_1 import enforce_clinical_proposal_semantic_guard
from evidence_binding_guard_v0_1 import enforce_evidence_binding
from context_budget_manager_v0_1 import (
    select_profile, budget_evidence, compact_packet_for_budget,
    response_contract, audit_prompt
)
from response_budget_guard_v0_1 import enforce_response_budget
from deterministic_response_assembler_v0_1 import assemble_biosafe_response
from compact_reasoning_recovery_v0_1 import recover_compact_reasoning

MODELS = ["qwen3.5:0.8b"]
MODEL_CONFIGS = {
    "qwen3.5:0.8b": {"temperature": 0.0, "num_predict": 420, "think": False},
    "qwen3.5:0.8b": {"temperature": 0.0, "num_predict": 420, "think": False},
}

def load_cases(path: Path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def load_doc(filename: str | None, docs_dir: Path) -> str:
    if not filename:
        return ""
    p = docs_dir / filename
    if not p.exists():
        raise FileNotFoundError(f"Missing benchmark document: {p}")
    return p.read_text(encoding="utf-8")

def build_structured_packet(adapter, case, docs_dir, bundle):
    ctx = case["document_context"]
    docs = []

    primary_name = ctx["primary_document_id"]
    primary_text = load_doc(primary_name, docs_dir)
    docs.append(adapter.analyse(primary_name, primary_text))

    secondary_name = ctx.get("secondary_document_id")
    secondary_text = ""
    if secondary_name:
        secondary_text = load_doc(secondary_name, docs_dir)
        docs.append(adapter.analyse(secondary_name, secondary_text))

    policy = bundle.get("policy_decision") or {}
    policy_mode = (
        policy.get("mode")
        or policy.get("response_mode")
        or str(policy.get("decision") or "DOCUMENT_REVIEW")
    )

    packet = adapter.build_packet(
        case["user_input"],
        docs,
        bundle.get("evidence_bundle", []),
        policy_mode,
    )
    return packet, primary_text, secondary_text


def document_types_from_packet(packet):
    return [
        x.get("document_type")
        for x in (packet.get("structured_facts") or [])
        if x.get("document_type")
    ]

def apply_document_context_evidence_filter(bundle, messages, packet, query):
    filtered, audit = filter_document_review_evidence(
        query=query,
        document_types=document_types_from_packet(packet),
        evidence_bundle=bundle.get("evidence_bundle", []),
    )
    bundle = dict(bundle)
    bundle["evidence_bundle"] = filtered
    messages = patch_message_evidence(messages, filtered)

    # Keep structured packet aligned with what the model actually sees.
    packet = dict(packet)
    packet["rag_evidence"] = filtered
    packet["evidence_filter_audit"] = audit
    return bundle, messages, packet, audit

def _compact_structured_packet(packet):
    """Keep only decision-relevant preprocessing findings.

    Do not send the model the full deterministic extraction object because that
    encourages small models to reproduce the packet instead of answering in the
    BioSafe output schema.
    """
    docs = []
    for d in packet.get("structured_facts", []):
        docs.append({
            "document_id": d.get("document_id"),
            "document_type": d.get("document_type"),
            "missing_fields": [
                {
                    "field": m.get("field"),
                    "severity": m.get("severity"),
                    "reason": m.get("reason"),
                }
                for m in d.get("missing_fields", [])
            ],
            "vague_or_ambiguous_statements": d.get("extraction_notes", []),
        })

    conflicts = []
    for c in packet.get("contradictions", []):
        conflicts.append({
            "field": c.get("field"),
            "document_a": c.get("document_a"),
            "value_a": c.get("value_a"),
            "document_b": c.get("document_b"),
            "value_b": c.get("value_b"),
            "status": c.get("status"),
            "finding_type": c.get("finding_type") or c.get("review_rule"),
        })

    return {
        "documents": docs,
        "cross_document_findings": conflicts,
        "policy_mode": packet.get("policy_mode"),
        "boundary": (
            "User documents are scenario evidence, not regulatory authority. "
            "Do not certify compliance. Do not invent absent facts. "
            "Do not silently resolve contradictions."
        ),
        "response_discipline": {
            "max_evidence_items": 3,
            "max_missing_information_items": 8,
            "max_recommended_next_step_items": 3,
            "max_limitations_items": 3,
            "instruction": "Be concise. Do not restate full documents or the preprocessing packet."
        },
    }


def inject_context(messages, case, packet, primary_text, secondary_text):
    ctx = case["document_context"]
    compact = _compact_structured_packet(packet)

    block = [
        "",
        "=== USER-SUPPLIED SYNTHETIC BENCHMARK DOCUMENT ===",
        f"Document ID: {ctx['primary_document_id']}",
        primary_text,
        "=== END PRIMARY DOCUMENT ===",
    ]
    if secondary_text:
        block.extend([
            "",
            "=== SECOND USER-SUPPLIED SYNTHETIC BENCHMARK DOCUMENT ===",
            f"Document ID: {ctx['secondary_document_id']}",
            secondary_text,
            "=== END SECONDARY DOCUMENT ===",
        ])

    block.extend([
        "",
        "=== STRUCTURED PRE-REVIEW FINDINGS ===",
        json.dumps(compact, ensure_ascii=False, separators=(",", ":")),
        "=== END STRUCTURED PRE-REVIEW FINDINGS ===",
        "",
        "Use the structured findings as review aids only.",
        "Do NOT reproduce, summarize, or reformat the structured packet itself.",
        "Answer the user's original question using the BioSafe response schema.",
        "",
        "FINAL OUTPUT REQUIREMENT — RETURN ONLY ONE JSON OBJECT WITH EXACTLY THESE TOP-LEVEL FIELDS:",
        "conclusion",
        "applicable_authority",
        "evidence",
        "missing_information",
        "recommended_next_step",
        "limitations",
        "safety",
        "",
        "Do not add analysis, summary, status, facts, document_type, or any other top-level field.",
        "Keep the response concise: at most 3 evidence items, 8 missing-information items, 3 next steps and 3 limitations.",
        "If cross-document findings are supplied, explicitly surface them; do not say that no inconsistency was found.",
        "Do not instruct a researcher/PI to submit, complete, provide or prepare an IBC Assessment Report; that is IBC-only.",
    ])
    addition = "\n".join(block)

    for i in range(len(messages)-1, -1, -1):
        if messages[i].get("role") == "user":
            messages[i] = dict(messages[i])
            messages[i]["content"] = messages[i].get("content", "") + addition
            return messages
    messages.append({"role": "user", "content": addition})
    return messages

def stream_chat(host, model, messages, cfg, timeout=1200):
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "format": "json",
        "options": {"temperature": cfg["temperature"], "num_predict": cfg["num_predict"]},
        "think": cfg["think"],
    }
    req = urllib.request.Request(
        host.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    first_event = None
    first_content = None
    content_parts = []
    thinking_chars = 0
    final = {}

    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            if not raw.strip():
                continue
            now = time.perf_counter()
            if first_event is None:
                first_event = now - t0
            obj = json.loads(raw.decode("utf-8"))
            msg = obj.get("message") or {}
            content = msg.get("content") or ""
            thinking = msg.get("thinking") or ""
            if content:
                if first_content is None:
                    first_content = now - t0
                content_parts.append(content)
            thinking_chars += len(thinking)
            if obj.get("done"):
                final = obj

    wall = time.perf_counter() - t0
    eval_count = final.get("eval_count") or 0
    eval_duration = final.get("eval_duration") or 0

    return {
        "content": "".join(content_parts),
        "thinking_chars": thinking_chars,
        "first_event_seconds": None if first_event is None else round(first_event, 4),
        "first_content_seconds": None if first_content is None else round(first_content, 4),
        "wall_seconds": round(wall, 4),
        "prompt_eval_count": final.get("prompt_eval_count") or 0,
        "eval_count": eval_count,
        "generation_tokens_per_second": (
            round(eval_count / (eval_duration / 1e9), 3)
            if eval_count and eval_duration else None
        ),
        "done_reason": final.get("done_reason"),
    }

def parse_json(content):
    try:
        return json.loads(content), True, None
    except Exception as exc:
        return None, False, str(exc)

def merged_decision(core, boundary):
    if core.decision == "HARD_FAIL":
        return "HARD_FAIL"
    if boundary.decision == "RETRY" or core.decision == "RETRY":
        return "RETRY"
    if boundary.decision == "PASS_WITH_WARNING" or core.decision == "PASS_WITH_WARNING":
        return "PASS_WITH_WARNING"
    return "PASS"

def process(parsed, bundle, valid_json):
    repairs = []
    if valid_json and isinstance(parsed, dict):
        parsed, r1 = normalize_output(parsed)
        repairs.extend(r1)
        parsed, r2 = enforce_policy_shell(parsed, bundle["policy_decision"])
        repairs.extend(r2)
        parsed, r3 = enforce_researcher_ibc_boundary(parsed)
        repairs.extend(r3)
        parsed, r4 = enforce_critical_missing_compliance_boundary(
            parsed, bundle["policy_decision"], bundle.get("_structured_packet", {})
        )
        repairs.extend(r4)

        parsed, r5 = normalize_document_evidence_aliases(
            parsed, bundle.get("evidence_bundle", [])
        )
        repairs.extend(r5)

        parsed, r6 = enforce_document_fact_precedence(
            parsed, bundle.get("_structured_packet", {})
        )
        repairs.extend(r6)

        parsed, r7 = enforce_retrieved_claim_semantic_consistency(
            parsed, bundle.get("evidence_bundle", [])
        )
        repairs.extend(r7)

        parsed, r8 = enforce_clinical_proposal_semantic_guard(
            parsed,
            bundle.get("_structured_packet", {}),
            bundle.get("evidence_bundle", []),
        )
        repairs.extend(r8)

        parsed, r9 = enforce_evidence_binding(
            parsed,
            bundle.get("evidence_bundle", []),
        )
        repairs.extend(r9)

        profile = select_profile(bundle.get("_model_id", "qwen3.5:0.8b"))
        parsed, r10 = enforce_response_budget(
            parsed,
            max_missing=profile.max_missing_findings,
            max_recommendations=profile.max_recommendations,
            max_limitations=profile.max_limitations,
            max_evidence=profile.max_rag_claims + min(profile.max_document_evidence, 3),
        )
        repairs.extend(r10)
    core = validate_output(parsed, bundle, valid_json=valid_json and isinstance(parsed, dict))
    boundary = validate_boundaries(parsed or {}, bundle["policy_decision"])
    return parsed, repairs, core, boundary, merged_decision(core, boundary)

def mean(vals):
    vals = [x for x in vals if isinstance(x, (int, float))]
    return round(statistics.mean(vals), 4) if vals else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen3.5:0.8b"])
    ap.add_argument(
        "--regression-only",
        action="store_true",
        help="Optional sanity check: run only PROP-002. Omit this flag for the full 16-case Standard evaluation."
    )
    ap.add_argument("--host", default=None)
    ap.add_argument("--timeout", type=int, default=1200)
    ap.add_argument("--data", default=str(PROJECT_ROOT/"data/BioSafe_Context_Aware_Document_Benchmark_v0.2.jsonl"))
    ap.add_argument("--docs", default=str(PROJECT_ROOT/"data/context_documents_v0_2"))
    ap.add_argument("--output-dir", default=str(PROJECT_ROOT/"output/qwen3_5_0_8b_16case_lite_comparison_v0_1"))
    args = ap.parse_args()

    host = (args.host or detect_host()).rstrip("/")
    ok, detail = check_server(host)
    if not ok:
        raise SystemExit(f"Ollama not reachable at {host}: {detail}")

    installed = set(model_names(host))
    missing = [m for m in args.models if m not in installed]
    if missing:
        raise SystemExit("Missing models: " + ", ".join(missing))

    cases = load_cases(Path(args.data))
    if args.regression_only:
        regression_ids = {"PROP-002"}
        cases = [c for c in cases if c.get("id") in regression_ids]
    docs_dir = Path(args.docs)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    pipe = BioSafePipelineV032(PROJECT_ROOT, 3)
    adapter = BioSafeStructuredBenchmarkAdapterV01(PROJECT_ROOT)

    master = {
        "suite": "BioSafe_Qwen3.5_0.8B_16Case_Lite_Comparison_v0.1",
        "cases": len(cases),
        "frozen_benchmark": "BioSafe_Context_Aware_Document_Benchmark_v0.2",
        "structured_layer": "BioSafe Structured Document Analysis Layer v1.0 — ARCHITECTURE_FROZEN",
        "pipeline": {
            "knowledge_base": "BioSafe KB v0.2",
            "retrieval": "CFG-02",
            "authority_router": "Integration Authority Router v0.1",
            "query_router": "Query Router v0.2",
            "scope_gate": "Scope Gate v0.2.1",
            "policy_guard": "Policy & Decision Guard v0.3.2",
            "normalizer": "Output Normalizer v0.3.2",
            "policy_shell": "Policy Shell Enforcer v0.3.2",
        },
        "models": {},
    }

    for model in args.models:
        cfg = MODEL_CONFIGS[model]
        safe = model.replace(":", "_").replace("/", "_")
        outfile = outdir/f"structured_context_doc_{safe}.jsonl"
        records = []

        with outfile.open("w", encoding="utf-8") as f:
            for idx, case in enumerate(cases, 1):
                bundle, messages, deterministic = pipe.build_messages(
                    case["user_input"], case["id"], case["safety_class"]
                )

                packet, primary_text, secondary_text = build_structured_packet(
                    adapter, case, docs_dir, bundle
                )

                bundle, messages, packet, evidence_filter_audit = apply_document_context_evidence_filter(
                    bundle, messages, packet, case["user_input"]
                )

                profile = select_profile(model)

                # Standard-Calibrated v0.2:
                # Keep Qwen3.5-2B as the model and preserve its Standard prompt budget,
                # but use the same compact reasoning envelope that passed for 0.8B Lite.
                calibrated_max_rag_claims = 3
                calibrated_max_document_evidence = 6
                calibrated_max_missing_findings = 3
                calibrated_max_recommendations = 2
                calibrated_max_limitations = 1

                bundle = merge_document_evidence_into_bundle(
                    bundle, packet, max_items=calibrated_max_document_evidence
                )

                from dataclasses import replace
                calibrated_profile = replace(
                    profile,
                    output_token_budget=420,
                    max_rag_claims=calibrated_max_rag_claims,
                    max_document_evidence=calibrated_max_document_evidence,
                    max_missing_findings=calibrated_max_missing_findings,
                    max_recommendations=calibrated_max_recommendations,
                    max_limitations=calibrated_max_limitations,
                )

                budgeted_evidence, evidence_budget_audit = budget_evidence(
                    bundle.get("evidence_bundle", []), calibrated_profile
                )
                bundle["evidence_bundle"] = budgeted_evidence
                bundle["_model_id"] = model

                packet = compact_packet_for_budget(packet, calibrated_profile)
                bundle["_structured_packet"] = packet

                messages = patch_message_evidence(
                    messages, bundle.get("evidence_bundle", [])
                )
                packet["rag_evidence"] = bundle.get("evidence_bundle", [])

                messages = inject_context(
                    messages, case, packet, primary_text, secondary_text
                )
                for mi in range(len(messages)-1, -1, -1):
                    if messages[mi].get("role") == "user":
                        messages[mi] = dict(messages[mi])
                        messages[mi]["content"] = (
                            messages[mi].get("content", "") + response_contract(calibrated_profile)
                        )
                        break

                context_budget_audit = audit_prompt(
                    model, messages, evidence_budget_audit
                )

                rec = {
                    "case_id": case["id"],
                    "category": case["category"],
                    "model_id": model,
                    "document_context": case["document_context"],
                    "expected_concepts": case["expected_concepts"],
                    "required_behaviour": case["required_behaviour"],
                    "must_not": case["must_not"],
                    "route": bundle["route"],
                    "evidence_ids": [x["evidence_id"] for x in bundle["evidence_bundle"]],
                    "evidence_filter_audit": evidence_filter_audit,
                    "policy_decision": bundle["policy_decision"],
                    "structured_analysis": packet,
                    "context_budget": context_budget_audit,
                    "calibration": {
                        "profile": "Qwen3.5-0.8B Lite Comparison v0.1",
                        "generation_budget": 420,
                        "max_rag_claims": 3,
                        "max_document_evidence": 6,
                        "max_missing_information": 3,
                        "max_recommended_next_step": 2,
                        "max_limitations": 1,
                        "comparison_target": "Qwen3.5-2B Standard-Calibrated v0.2"
                    },
                }

                if deterministic is not None:
                    parsed, repairs, core, boundary, decision = process(deterministic, bundle, True)
                    rec.update({
                        "model_called": False,
                        "raw_output": None,
                        "parsed_output": parsed,
                        "valid_json": True,
                        "parse_error": None,
                        "contradiction_fallback_used": False,
                        "deterministic_repairs": repairs,
                        "core_validation": core.to_dict(),
                        "boundary_validation": boundary.to_dict(),
                        "final_decision": decision,
                        "metrics": {"done_reason": "deterministic", "wall_seconds": 0.0},
                    })
                elif bundle["policy_decision"].get("mode") == "SOURCE_ONLY_DRAFT":
                    parsed0 = build_source_only_draft_response(
                        packet, bundle.get("evidence_bundle", [])
                    )
                    parsed, repairs, core, boundary, decision = process(parsed0, bundle, True)
                    repairs.append("SOURCE_ONLY_DRAFT_COMPACT_RENDERER: deterministic source-only response")
                    rec.update({
                        "model_called": False,
                        "raw_output": None,
                        "parsed_output": parsed,
                        "valid_json": True,
                        "parse_error": None,
                        "contradiction_fallback_used": False,
                        "deterministic_repairs": repairs,
                        "core_validation": core.to_dict(),
                        "boundary_validation": boundary.to_dict(),
                        "final_decision": decision,
                        "metrics": {"done_reason": "deterministic_source_only", "wall_seconds": 0.0},
                    })
                else:
                    try:
                        gen = stream_chat(host, model, messages, cfg, timeout=args.timeout)
                    except (ConnectionResetError, urllib.error.URLError) as exc:
                        print(f"Transient Ollama transport error for {case['id']}: {exc!r}; retrying once.", flush=True)
                        time.sleep(0.5)
                        gen = stream_chat(host, model, messages, cfg, timeout=args.timeout)

                    compact0, compact_valid, err = recover_compact_reasoning(gen["content"])

                    contradiction_fallback_used = False
                    if compact0 is None and packet.get("contradictions"):
                        parsed0 = build_compact_contradiction_fallback(
                            packet, bundle.get("evidence_bundle", [])
                        )
                        valid = True
                        err = None
                        contradiction_fallback_used = True
                    elif compact0 is None:
                        parsed0 = None
                        valid = False
                    else:
                        parsed0 = assemble_biosafe_response(
                            compact0,
                            bundle,
                            max_missing=calibrated_profile.max_missing_findings,
                            max_recommendations=calibrated_profile.max_recommendations,
                            max_evidence=calibrated_profile.max_rag_claims,
                            max_limitations=calibrated_profile.max_limitations,
                        )
                        valid = True

                    parsed, repairs, core, boundary, decision = process(parsed0, bundle, valid)
                    if contradiction_fallback_used:
                        repairs.append("COMPACT_CONTRADICTION_FALLBACK: replaced invalid/truncated model output")

                    rec.update({
                        "model_called": True,
                        "raw_output": gen["content"],
                        "parsed_output": parsed,
                        "valid_json": valid,
                        "compact_model_json_valid": compact_valid if compact0 is not None else False,
                        "parse_error": err,
                        "contradiction_fallback_used": contradiction_fallback_used,
                        "deterministic_repairs": repairs,
                        "core_validation": core.to_dict(),
                        "boundary_validation": boundary.to_dict(),
                        "final_decision": decision,
                        "metrics": gen,
                    })

                records.append(rec)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()

                sa = packet
                print(
                    f"[{idx:02d}/{len(cases)}] {model} {case['id']} "
                    f"{rec['final_decision']} JSON={rec['valid_json']} "
                    f"missing={len(sa.get('missing_information', []))} "
                    f"conflicts={len(sa.get('contradictions', []))} "
                    f"wall={rec.get('metrics',{}).get('wall_seconds')}s"
                )

        calls = [r for r in records if r.get("model_called")]
        decisions = {}
        for r in records:
            decisions[r["final_decision"]] = decisions.get(r["final_decision"], 0) + 1

        master["models"][model] = {
            "configuration": cfg,
            "cases": len(records),
            "valid_json_first_pass": sum(1 for r in calls if r.get("valid_json")),
            "decisions": decisions,
            "cases_with_repairs": sum(1 for r in records if r.get("deterministic_repairs")),
            "contradiction_fallbacks": sum(1 for r in records if r.get("contradiction_fallback_used")),
            "evidence_filtered_cases": sum(
                1 for r in records if r.get("evidence_filter_audit", {}).get("suppressed_evidence_ids")
            ),
            "length_exhaustions": sum(
                1 for r in calls if r.get("metrics", {}).get("done_reason") == "length"
            ),
            "mean_wall_seconds": mean([r.get("metrics",{}).get("wall_seconds") for r in calls]),
            "mean_first_content_seconds": mean([r.get("metrics",{}).get("first_content_seconds") for r in calls]),
            "mean_generation_tokens_per_second": mean([
                r.get("metrics",{}).get("generation_tokens_per_second") for r in calls
            ]),
            "structured_cases_with_missing_fields": sum(
                1 for r in records if r["structured_analysis"].get("missing_information")
            ),
            "structured_cases_with_contradictions": sum(
                1 for r in records if r["structured_analysis"].get("contradictions")
            ),
            "output_file": str(outfile),
        }

    summary = outdir/"structured_context_document_benchmark_summary.json"
    summary.write_text(json.dumps(master, indent=2), encoding="utf-8")
    print("Summary:", summary)

if __name__ == "__main__":
    main()
