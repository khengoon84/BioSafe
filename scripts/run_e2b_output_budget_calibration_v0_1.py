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

MODEL = "gemma4:e2b"
TARGET_IDS = ["BS-005", "PROP-004"]
TOKEN_BUDGETS = [450, 550]


def stream_chat(
    host: str,
    model: str,
    messages: List[Dict[str, str]],
    num_predict: int,
    timeout: int = 600,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "format": "json",
        "think": False,
        "options": {
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 64,
            "num_predict": num_predict,
        },
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
        "thinking": "".join(thinking_parts),
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--output-dir", default=None)
    ap.add_argument(
        "--always-run-both",
        action="store_true",
        help="Run both 450 and 550 even if 450 already completes successfully.",
    )
    args = ap.parse_args()

    host = (args.host or detect_host()).rstrip("/")
    ok, detail = check_server(host)
    if not ok:
        raise SystemExit(f"Ollama not reachable at {host}: {detail}")

    installed = set(model_names(host))
    if MODEL not in installed:
        raise SystemExit(f"{MODEL} is not installed.")

    pipe = BioSafePipelineV032(ROOT, 3)
    all_cases = load_benchmark(ROOT / "data/BioSafe_Benchmark_Dataset_v0.1.jsonl")
    by_id = {c["id"]: c for c in all_cases}

    outdir = Path(args.output_dir) if args.output_dir else ROOT / "output" / "e2b_budget_calibration_v0_1"
    outdir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []

    for case_id in TARGET_IDS:
        case = by_id[case_id]
        bundle, messages, deterministic = pipe.build_messages(
            case["user_input"], case["id"], case["safety_class"]
        )

        if deterministic is not None:
            raise RuntimeError(f"Unexpected deterministic short-circuit for {case_id}")

        print(f"\n=== {case_id} ===")

        completed = False
        for budget in TOKEN_BUDGETS:
            if completed and not args.always_run_both:
                break

            print(f"Running {MODEL} with num_predict={budget} ...")
            gen = stream_chat(host, MODEL, messages, budget, timeout=args.timeout)
            parsed0, valid_json, parse_error = parse_json(gen["content"])
            parsed, repairs, core, boundary, decision = process_output(
                parsed0, bundle, valid_json
            )

            rec = {
                "case_id": case_id,
                "model_id": MODEL,
                "inference_config": {
                    "think": False,
                    "temperature": 1.0,
                    "top_p": 0.95,
                    "top_k": 64,
                    "num_predict": budget,
                },
                "policy_decision": bundle["policy_decision"],
                "route": bundle["route"],
                "evidence_ids": [x["evidence_id"] for x in bundle["evidence_bundle"]],
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
            }

            complete_json = valid_json and gen["done_reason"] != "length"
            acceptable = complete_json and decision in ("PASS", "PASS_WITH_WARNING")
            rec["complete_json"] = complete_json
            rec["acceptable_without_retry"] = acceptable

            records.append(rec)

            print(
                f"{case_id} @ {budget}: "
                f"decision={decision} | JSON={valid_json} | "
                f"done={gen['done_reason']} | "
                f"TTFC={gen['first_content_seconds']}s | "
                f"wall={gen['wall_seconds']}s | "
                f"tok/s={gen['generation_tokens_per_second']} | "
                f"repairs={len(repairs)}"
            )

            if acceptable:
                completed = True
                print(f"Minimum acceptable budget for {case_id}: {budget}")

    outfile = outdir / "e2b_budget_calibration_results.jsonl"
    with outfile.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    case_summary: Dict[str, Any] = {}
    for case_id in TARGET_IDS:
        rs = [r for r in records if r["case_id"] == case_id]
        successful = [r for r in rs if r["acceptable_without_retry"]]
        case_summary[case_id] = {
            "attempts": [
                {
                    "num_predict": r["inference_config"]["num_predict"],
                    "valid_json": r["valid_json"],
                    "done_reason": r["metrics"]["done_reason"],
                    "decision": r["final_decision"],
                    "first_content_seconds": r["metrics"]["first_content_seconds"],
                    "wall_seconds": r["metrics"]["wall_seconds"],
                    "repairs": r["deterministic_repairs"],
                }
                for r in rs
            ],
            "minimum_acceptable_budget": (
                min(r["inference_config"]["num_predict"] for r in successful)
                if successful else None
            ),
        }

    successful_all = all(
        case_summary[c]["minimum_acceptable_budget"] is not None for c in TARGET_IDS
    )
    max_min_budget = (
        max(case_summary[c]["minimum_acceptable_budget"] for c in TARGET_IDS)
        if successful_all else None
    )

    if successful_all and max_min_budget <= 450:
        recommendation = "ADVANCE_E2B_TO_13_CASE"
    elif successful_all and max_min_budget <= 550:
        recommendation = "CONDITIONAL_ADVANCE_REVIEW_LATENCY"
    else:
        recommendation = "STOP_E2B_TEXT_BRANCH"

    summary = {
        "suite": "BioSafe_E2B_Output_Budget_Calibration_v0.1",
        "model": MODEL,
        "cases": TARGET_IDS,
        "token_budgets": TOKEN_BUDGETS,
        "inference_mode": {
            "think": False,
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 64,
        },
        "case_summary": case_summary,
        "all_cases_completed": successful_all,
        "minimum_budget_covering_all_cases": max_min_budget,
        "provisional_recommendation": recommendation,
        "notes": [
            "The recommendation is provisional and must be paired with manual substantive review.",
            "A PASS here means complete JSON plus validator PASS/PASS_WITH_WARNING without LLM retry.",
        ],
    }

    summary_file = outdir / "e2b_budget_calibration_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n=== CALIBRATION SUMMARY ===")
    for case_id, s in case_summary.items():
        print(f"{case_id}: minimum acceptable budget = {s['minimum_acceptable_budget']}")
    print("Overall minimum budget:", max_min_budget)
    print("Recommendation:", recommendation)
    print("\nResults:", outfile)
    print("Summary:", summary_file)


if __name__ == "__main__":
    main()
