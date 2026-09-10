#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from biosafe_pipeline_v0_1 import load_benchmark
from biosafe_pipeline_v0_3_2 import BioSafePipelineV032
from output_validator_v0_2 import validate_output
from boundary_validator_v0_3_2 import validate_boundaries
from output_normalizer_v0_3_2 import normalize_output
from policy_shell_enforcer_v0_3_2 import enforce_policy_shell
from run_model_compatibility_v0_1 import check_server, detect_host, model_names, running_models

MODELS = ["qwen3.5:0.8b"]

MODEL_CONFIGS = {
    "qwen3.5:0.8b": {
        "temperature": 0.0,
        "num_predict": 700,
        "think": False,
        "label": "Qwen3.5 0.8B Challenger",
    },
}


def stream_chat(
    host: str,
    model: str,
    messages: List[Dict[str, str]],
    cfg: Dict[str, Any],
    timeout: int = 900,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "format": "json",
        "options": {
            "temperature": cfg["temperature"],
            "num_predict": cfg["num_predict"],
        },
    }
    if cfg.get("think") is not None:
        payload["think"] = cfg["think"]

    req = urllib.request.Request(
        host.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    t0 = time.perf_counter()
    first_event = None
    first_content = None
    content_parts: List[str] = []
    thinking_parts: List[str] = []
    final: Dict[str, Any] = {}

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
            if thinking:
                thinking_parts.append(thinking)

            if obj.get("done"):
                final = obj

    wall = time.perf_counter() - t0
    eval_count = final.get("eval_count") or 0
    eval_duration = final.get("eval_duration") or 0
    return {
        "content": "".join(content_parts),
        "thinking_chars": sum(len(x) for x in thinking_parts),
        "wall_seconds": round(wall, 4),
        "first_event_seconds": None if first_event is None else round(first_event, 4),
        "first_content_seconds": None if first_content is None else round(first_content, 4),
        "ollama_total_seconds": round((final.get("total_duration") or 0) / 1e9, 4),
        "ollama_load_seconds": round((final.get("load_duration") or 0) / 1e9, 4),
        "prompt_eval_count": final.get("prompt_eval_count") or 0,
        "prompt_eval_seconds": round((final.get("prompt_eval_duration") or 0) / 1e9, 4),
        "eval_count": eval_count,
        "eval_seconds": round(eval_duration / 1e9, 4),
        "generation_tokens_per_second": (
            round(eval_count / (eval_duration / 1e9), 3)
            if eval_count and eval_duration else None
        ),
        "done_reason": final.get("done_reason"),
    }


def parse_json(content: str) -> Tuple[Any, bool, str | None]:
    try:
        return json.loads(content), True, None
    except Exception as exc:
        return None, False, str(exc)


def merged_decision(core, boundary) -> str:
    if core.decision == "HARD_FAIL":
        return "HARD_FAIL"
    if boundary.decision == "RETRY" or core.decision == "RETRY":
        return "RETRY"
    if boundary.decision == "PASS_WITH_WARNING" or core.decision == "PASS_WITH_WARNING":
        return "PASS_WITH_WARNING"
    return "PASS"


def process_output(parsed: Any, bundle: Dict[str, Any], valid_json: bool):
    repairs: List[str] = []
    if valid_json and isinstance(parsed, dict):
        parsed, r1 = normalize_output(parsed)
        repairs.extend(r1)
        parsed, r2 = enforce_policy_shell(parsed, bundle["policy_decision"])
        repairs.extend(r2)

    core = validate_output(parsed, bundle, valid_json=valid_json and isinstance(parsed, dict))
    boundary = validate_boundaries(parsed or {}, bundle["policy_decision"])
    return parsed, repairs, core, boundary, merged_decision(core, boundary)


def mean_or_none(vals):
    vals = [x for x in vals if isinstance(x, (int, float))]
    return round(statistics.mean(vals), 4) if vals else None


def median_or_none(vals):
    vals = [x for x in vals if isinstance(x, (int, float))]
    return round(statistics.median(vals), 4) if vals else None


def category_summary(records):
    out = {}
    cats = sorted(set(r["category"] for r in records))
    for cat in cats:
        rs = [r for r in records if r["category"] == cat]
        decisions = {}
        for r in rs:
            decisions[r["final_decision"]] = decisions.get(r["final_decision"], 0) + 1
        out[cat] = {
            "cases": len(rs),
            "decisions": decisions,
            "valid_json_first_pass": sum(1 for r in rs if r.get("valid_json")),
            "cases_with_repairs": sum(1 for r in rs if r.get("deterministic_repairs")),
            "mean_wall_seconds": mean_or_none([r.get("metrics", {}).get("wall_seconds") for r in rs if r.get("model_called")]),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--host", default=None)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()

    host = (args.host or detect_host()).rstrip("/")
    ok, detail = check_server(host)
    if not ok:
        raise SystemExit(f"Ollama not reachable at {host}: {detail}")

    installed = set(model_names(host))
    missing = [m for m in args.models if m not in installed]
    if missing:
        raise SystemExit("Missing models: " + ", ".join(missing))

    unknown = [m for m in args.models if m not in MODEL_CONFIGS]
    if unknown:
        raise SystemExit("No config defined for: " + ", ".join(unknown))

    pipe = BioSafePipelineV032(ROOT, 3)
    cases = load_benchmark(ROOT / "data/BioSafe_Benchmark_Dataset_v0.1.jsonl")

    outdir = Path(args.output_dir) if args.output_dir else ROOT / "output" / "qwen3_5_0_8b_50case_challenger_v0_2"
    outdir.mkdir(parents=True, exist_ok=True)

    master_summary = {
        "suite": "BioSafe_Qwen3.5_0.8B_50Case_Challenger_v0.2",
        "pipeline": {
            "knowledge_base": "BioSafe KB v0.2",
            "retrieval": "CFG-02",
            "authority_router": "Integration Authority Router v0.1",
            "query_router": "Query Router v0.2",
            "scope_gate": "Scope Gate v0.2.1",
            "policy_guard": "Policy & Decision Guard v0.3.2",
            "normalizer": "Output Normalizer v0.3.2",
            "policy_shell": "Policy Shell Enforcer v0.3.2",
            "validators": ["Output Validator", "Boundary Validator"],
        },
        "benchmark_cases": len(cases),
        "models": {},
    }

    for model in args.models:
        cfg = MODEL_CONFIGS[model]
        print(f"\n=== {cfg['label']} ({model}) ===")
        safe = model.replace(":", "_").replace("/", "_")
        outfile = outdir / f"baseline_{safe}_50case.jsonl"
        records = []

        with outfile.open("w", encoding="utf-8") as f:
            for idx, case in enumerate(cases, 1):
                bundle, messages, deterministic = pipe.build_messages(
                    case["user_input"], case["id"], case["safety_class"]
                )

                rec = {
                    "case_id": case["id"],
                    "category": case.get("category"),
                    "safety_class": case.get("safety_class"),
                    "model_id": model,
                    "model_label": cfg["label"],
                    "policy_decision": bundle["policy_decision"],
                    "route": bundle["route"],
                    "evidence_ids": [x["evidence_id"] for x in bundle["evidence_bundle"]],
                    "model_called": deterministic is None,
                }

                if deterministic is not None:
                    parsed, repairs, core, boundary, decision = process_output(
                        deterministic, bundle, True
                    )
                    rec.update({
                        "generation_mode": "deterministic_short_circuit",
                        "raw_output": None,
                        "thinking": "",
                        "thinking_chars": 0,
                        "parsed_output": parsed,
                        "valid_json": True,
                        "parse_error": None,
                        "deterministic_repairs": repairs,
                        "core_validation": core.to_dict(),
                        "boundary_validation": boundary.to_dict(),
                        "final_decision": decision,
                        "metrics": {
                            "first_event_seconds": 0.0,
                            "first_content_seconds": 0.0,
                            "wall_seconds": 0.0,
                            "generation_tokens_per_second": None,
                            "done_reason": "deterministic",
                        },
                    })
                else:
                    try:
                        gen = stream_chat(host, model, messages, cfg, timeout=args.timeout)
                        parsed0, valid_json, parse_error = parse_json(gen["content"])
                        parsed, repairs, core, boundary, decision = process_output(
                            parsed0, bundle, valid_json
                        )

                        rec.update({
                            "generation_mode": "model",
                            "raw_output": gen["content"],
                            "thinking": gen["thinking"],
                            "thinking_chars": gen["thinking_chars"],
                            "parsed_output": parsed,
                            "valid_json": valid_json,
                            "parse_error": parse_error,
                            "deterministic_repairs": repairs,
                            "core_validation": core.to_dict(),
                            "boundary_validation": boundary.to_dict(),
                            "final_decision": decision,
                            "metrics": {
                                k: gen.get(k)
                                for k in [
                                    "first_event_seconds",
                                    "first_content_seconds",
                                    "wall_seconds",
                                    "ollama_total_seconds",
                                    "ollama_load_seconds",
                                    "prompt_eval_count",
                                    "prompt_eval_seconds",
                                    "eval_count",
                                    "eval_seconds",
                                    "generation_tokens_per_second",
                                    "done_reason",
                                ]
                            },
                            "ollama_ps_after_case": running_models(host),
                        })
                    except Exception as exc:
                        rec.update({
                            "generation_mode": "model",
                            "raw_output": "",
                            "thinking": "",
                            "thinking_chars": 0,
                            "parsed_output": None,
                            "valid_json": False,
                            "parse_error": repr(exc),
                            "deterministic_repairs": [],
                            "core_validation": None,
                            "boundary_validation": None,
                            "final_decision": "HARD_FAIL",
                            "metrics": {},
                            "error": repr(exc),
                        })

                records.append(rec)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()

                m = rec.get("metrics", {})
                print(
                    f"[{idx:02d}/{len(cases)}] {case['id']}: "
                    f"{rec['final_decision']} | JSON={rec.get('valid_json')} | "
                    f"wall={m.get('wall_seconds')}s | "
                    f"repairs={len(rec.get('deterministic_repairs', []))}"
                )

        model_calls = [r for r in records if r["model_called"]]
        decisions = {}
        for r in records:
            decisions[r["final_decision"]] = decisions.get(r["final_decision"], 0) + 1

        model_summary = {
            "label": cfg["label"],
            "configuration": cfg,
            "output_file": str(outfile),
            "cases": len(records),
            "model_calls": len(model_calls),
            "deterministic_short_circuits": len(records) - len(model_calls),
            "valid_json_first_pass": sum(1 for r in model_calls if r.get("valid_json")),
            "invalid_json_first_pass": sum(1 for r in model_calls if not r.get("valid_json")),
            "decisions": decisions,
            "cases_with_any_repair": sum(1 for r in records if r.get("deterministic_repairs")),
            "total_repairs": sum(len(r.get("deterministic_repairs", [])) for r in records),
            "schema_repairs": sum(
                sum(1 for x in r.get("deterministic_repairs", []) if x.startswith("schema:"))
                for r in records
            ),
            "policy_shell_repairs": sum(
                sum(1 for x in r.get("deterministic_repairs", []) if x.startswith("policy:"))
                for r in records
            ),
            "length_exhaustions": sum(
                1 for r in model_calls if r.get("metrics", {}).get("done_reason") == "length"
            ),
            "cases_with_thinking_output": sum(
                1 for r in model_calls if (r.get("thinking_chars") or 0) > 0
            ),
            "mean_first_content_seconds": mean_or_none([
                r.get("metrics", {}).get("first_content_seconds") for r in model_calls
            ]),
            "median_first_content_seconds": median_or_none([
                r.get("metrics", {}).get("first_content_seconds") for r in model_calls
            ]),
            "mean_wall_seconds": mean_or_none([
                r.get("metrics", {}).get("wall_seconds") for r in model_calls
            ]),
            "median_wall_seconds": median_or_none([
                r.get("metrics", {}).get("wall_seconds") for r in model_calls
            ]),
            "mean_generation_tokens_per_second": mean_or_none([
                r.get("metrics", {}).get("generation_tokens_per_second") for r in model_calls
            ]),
            "by_category": category_summary(records),
        }

        master_summary["models"][model] = model_summary

    summary_path = outdir / "baseline_50case_summary.json"
    summary_path.write_text(json.dumps(master_summary, indent=2), encoding="utf-8")
    print("\nSummary:", summary_path)


if __name__ == "__main__":
    main()
