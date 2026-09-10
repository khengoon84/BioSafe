#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
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
from run_model_compatibility_v0_1 import check_server, detect_host, model_names, running_models, stream_chat

DEFAULT_MODELS = ["qwen3:0.6b", "qwen3:1.7b", "gemma4:e2b", "gemma4:e4b"]
TARGET_IDS = ["BS-005", "BS-007", "MY-006", "PROP-004", "FORM-002"]


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
    final = merged_decision(core, boundary)
    return parsed, repairs, core, boundary, final


def mean_or_none(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(statistics.mean(vals), 4) if vals else None


def median_or_none(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(statistics.median(vals), 4) if vals else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--host", default=None)
    ap.add_argument("--num-predict", type=int, default=700)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--output-dir", default=None)
    args = ap.parse_args()

    host = (args.host or detect_host()).rstrip("/")
    ok, detail = check_server(host)
    if not ok:
        raise SystemExit(f"Ollama not reachable at {host}: {detail}")

    installed = set(model_names(host))
    missing = [m for m in args.models if m not in installed]
    if missing:
        raise SystemExit(
            "Missing models: " + ", ".join(missing)
            + "\nInstall them first with Ollama, then rerun."
        )

    pipe = BioSafePipelineV032(ROOT, 3)
    all_cases = load_benchmark(ROOT / "data/BioSafe_Benchmark_Dataset_v0.1.jsonl")
    by_id = {c["id"]: c for c in all_cases}
    cases = [by_id[cid] for cid in TARGET_IDS]

    outdir = Path(args.output_dir) if args.output_dir else ROOT / "output" / "gemma4_compare_v0_1"
    outdir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "suite": "BioSafe_Gemma4_5Case_Comparison_v0.1",
        "target_case_ids": TARGET_IDS,
        "num_predict": args.num_predict,
        "models": {},
    }

    for model in args.models:
        print(f"\n=== {model} ===")
        model_safe = model.replace(":", "_").replace("/", "_")
        outfile = outdir / f"five_case_{model_safe}.jsonl"

        records: List[Dict[str, Any]] = []
        with outfile.open("w", encoding="utf-8") as f:
            for case in cases:
                bundle, messages, deterministic = pipe.build_messages(
                    case["user_input"], case["id"], case["safety_class"]
                )
                rec: Dict[str, Any] = {
                    "case_id": case["id"],
                    "model_id": model,
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
                        "parsed_output": parsed,
                        "valid_json": True,
                        "deterministic_repairs": repairs,
                        "core_validation": core.to_dict(),
                        "boundary_validation": boundary.to_dict(),
                        "final_decision": decision,
                        "metrics": {
                            "first_event_seconds": 0.0,
                            "first_content_seconds": 0.0,
                            "wall_seconds": 0.0,
                            "ollama_load_seconds": 0.0,
                            "prompt_eval_count": 0,
                            "prompt_eval_seconds": 0.0,
                            "eval_count": 0,
                            "eval_seconds": 0.0,
                            "generation_tokens_per_second": None,
                        },
                    })
                else:
                    try:
                        gen = stream_chat(
                            host,
                            model,
                            messages,
                            num_predict=args.num_predict,
                            temperature=0.0,
                            timeout=args.timeout,
                            fmt="json",
                        )
                        parsed0, valid_json, parse_error = parse_json(gen["content"])
                        parsed, repairs, core, boundary, decision = process_output(
                            parsed0, bundle, valid_json
                        )
                        rec.update({
                            "generation_mode": "model",
                            "raw_output": gen["content"],
                            "thinking": gen.get("thinking"),
                            "parsed_output": parsed,
                            "valid_json": valid_json,
                            "parse_error": parse_error,
                            "deterministic_repairs": repairs,
                            "core_validation": core.to_dict(),
                            "boundary_validation": boundary.to_dict(),
                            "final_decision": decision,
                            "metrics": {k: gen.get(k) for k in [
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
                            ]},
                            "ollama_ps_after_case": running_models(host),
                        })
                    except Exception as exc:
                        rec.update({
                            "generation_mode": "model",
                            "valid_json": False,
                            "final_decision": "HARD_FAIL",
                            "error": repr(exc),
                            "deterministic_repairs": [],
                            "metrics": {},
                        })

                records.append(rec)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()

                m = rec.get("metrics", {})
                print(
                    f"{case['id']}: {rec['final_decision']} | "
                    f"TTFC={m.get('first_content_seconds')}s | "
                    f"wall={m.get('wall_seconds')}s | "
                    f"tok/s={m.get('generation_tokens_per_second')} | "
                    f"repairs={len(rec.get('deterministic_repairs', []))}"
                )

        model_calls = [r for r in records if r["model_called"]]
        decisions = {}
        for r in records:
            decisions[r["final_decision"]] = decisions.get(r["final_decision"], 0) + 1

        summary["models"][model] = {
            "output_file": str(outfile),
            "cases": len(records),
            "model_calls": len(model_calls),
            "valid_json_first_pass": sum(1 for r in model_calls if r.get("valid_json")),
            "deterministic_repairs": sum(len(r.get("deterministic_repairs", [])) for r in records),
            "policy_shell_repairs": sum(
                sum(1 for x in r.get("deterministic_repairs", []) if x.startswith("policy:"))
                for r in records
            ),
            "schema_repairs": sum(
                sum(1 for x in r.get("deterministic_repairs", []) if x.startswith("schema:"))
                for r in records
            ),
            "decisions": decisions,
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
            "mean_load_seconds": mean_or_none([
                r.get("metrics", {}).get("ollama_load_seconds") for r in model_calls
            ]),
        }

    summary_file = outdir / "comparison_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== SUMMARY ===")
    for model, s in summary["models"].items():
        print(
            f"{model}: decisions={s['decisions']} | "
            f"JSON={s['valid_json_first_pass']}/{s['model_calls']} | "
            f"repairs={s['deterministic_repairs']} | "
            f"mean TTFC={s['mean_first_content_seconds']}s | "
            f"mean wall={s['mean_wall_seconds']}s | "
            f"mean tok/s={s['mean_generation_tokens_per_second']}"
        )
    print("\nSummary:", summary_file)


if __name__ == "__main__":
    main()
