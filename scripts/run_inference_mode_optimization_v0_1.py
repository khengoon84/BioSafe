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

TARGET_IDS = ["BS-005", "BS-007", "MY-006", "PROP-004", "FORM-002"]

MODEL_CONFIGS = {
    "qwen3:0.6b": {
        "think": None,  # preserve prior baseline behaviour
        "temperature": 0.0,
        "top_p": None,
        "top_k": None,
        "num_predict": 350,
        "label": "Qwen3 0.6B baseline",
    },
    "gemma4:e2b": {
        "think": False,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 64,
        "num_predict": 350,
        "label": "Gemma 4 E2B no-thinking",
    },
    "gemma4:e4b": {
        "think": False,
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 64,
        "num_predict": 350,
        "label": "Gemma 4 E4B no-thinking",
    },
}


def stream_chat_custom(
    host: str,
    model: str,
    messages: List[Dict[str, str]],
    cfg: Dict[str, Any],
    timeout: int = 600,
) -> Dict[str, Any]:
    options: Dict[str, Any] = {
        "temperature": cfg["temperature"],
        "num_predict": cfg["num_predict"],
    }
    if cfg.get("top_p") is not None:
        options["top_p"] = cfg["top_p"]
    if cfg.get("top_k") is not None:
        options["top_k"] = cfg["top_k"]

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
        "format": "json",
        "options": options,
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
    prompt_eval_count = final.get("prompt_eval_count") or 0
    prompt_eval_duration = final.get("prompt_eval_duration") or 0

    return {
        "content": "".join(content_parts),
        "thinking": "".join(thinking_parts),
        "thinking_chars": sum(len(x) for x in thinking_parts),
        "wall_seconds": round(wall, 4),
        "first_event_seconds": None if first_event is None else round(first_event, 4),
        "first_content_seconds": None if first_content is None else round(first_content, 4),
        "ollama_total_seconds": round((final.get("total_duration") or 0) / 1e9, 4),
        "ollama_load_seconds": round((final.get("load_duration") or 0) / 1e9, 4),
        "prompt_eval_count": prompt_eval_count,
        "prompt_eval_seconds": round(prompt_eval_duration / 1e9, 4),
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


def advancement_label(summary: Dict[str, Any]) -> str:
    hard = summary["decisions"].get("HARD_FAIL", 0)
    retry = summary["decisions"].get("RETRY", 0)
    valid = summary["valid_json_first_pass"]
    calls = summary["model_calls"]
    wall = summary.get("mean_wall_seconds")
    first = summary.get("mean_first_content_seconds")

    if hard or retry:
        return "DO_NOT_ADVANCE"
    if valid < calls:
        return "DO_NOT_ADVANCE"
    if wall is None or first is None:
        return "DO_NOT_ADVANCE"
    if wall <= 50 and first <= 25:
        return "ADVANCE_LATENCY_GATE"
    if wall <= 60 and first <= 30:
        return "BORDERLINE_REVIEW"
    return "HOLD_LATENCY"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--models",
        nargs="+",
        default=["qwen3:0.6b", "gemma4:e2b", "gemma4:e4b"],
    )
    ap.add_argument("--host", default=None)
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
        raise SystemExit("Missing models: " + ", ".join(missing))

    unknown = [m for m in args.models if m not in MODEL_CONFIGS]
    if unknown:
        raise SystemExit("No optimization configuration defined for: " + ", ".join(unknown))

    pipe = BioSafePipelineV032(ROOT, 3)
    all_cases = load_benchmark(ROOT / "data/BioSafe_Benchmark_Dataset_v0.1.jsonl")
    by_id = {c["id"]: c for c in all_cases}
    cases = [by_id[cid] for cid in TARGET_IDS]

    outdir = Path(args.output_dir) if args.output_dir else ROOT / "output" / "inference_mode_v0_1"
    outdir.mkdir(parents=True, exist_ok=True)

    summary: Dict[str, Any] = {
        "suite": "BioSafe_Inference_Mode_Optimization_v0.1",
        "protected_pipeline": "Policy & Decision Guard v0.3.2",
        "target_case_ids": TARGET_IDS,
        "models": {},
    }

    for model in args.models:
        cfg = MODEL_CONFIGS[model]
        model_safe = model.replace(":", "_").replace("/", "_")
        outfile = outdir / f"optimized_{model_safe}.jsonl"
        records: List[Dict[str, Any]] = []

        print(f"\n=== {cfg['label']} ({model}) ===")
        print(
            f"think={cfg['think']} temp={cfg['temperature']} "
            f"top_p={cfg['top_p']} top_k={cfg['top_k']} "
            f"num_predict={cfg['num_predict']}"
        )

        with outfile.open("w", encoding="utf-8") as f:
            for case in cases:
                bundle, messages, deterministic = pipe.build_messages(
                    case["user_input"], case["id"], case["safety_class"]
                )

                rec: Dict[str, Any] = {
                    "case_id": case["id"],
                    "model_id": model,
                    "model_label": cfg["label"],
                    "inference_config": cfg,
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
                        gen = stream_chat_custom(
                            host, model, messages, cfg, timeout=args.timeout
                        )
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
                            "parse_error": repr(exc),
                            "raw_output": "",
                            "thinking": "",
                            "thinking_chars": 0,
                            "parsed_output": None,
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
                    f"{case['id']}: {rec['final_decision']} | "
                    f"JSON={rec.get('valid_json')} | "
                    f"TTFC={m.get('first_content_seconds')}s | "
                    f"wall={m.get('wall_seconds')}s | "
                    f"tok/s={m.get('generation_tokens_per_second')} | "
                    f"think_chars={rec.get('thinking_chars')} | "
                    f"repairs={len(rec.get('deterministic_repairs', []))}"
                )

        model_calls = [r for r in records if r["model_called"]]
        decisions: Dict[str, int] = {}
        for r in records:
            decisions[r["final_decision"]] = decisions.get(r["final_decision"], 0) + 1

        s = {
            "label": cfg["label"],
            "inference_config": cfg,
            "output_file": str(outfile),
            "cases": len(records),
            "model_calls": len(model_calls),
            "valid_json_first_pass": sum(1 for r in model_calls if r.get("valid_json")),
            "deterministic_repairs": sum(len(r.get("deterministic_repairs", [])) for r in records),
            "schema_repairs": sum(
                sum(1 for x in r.get("deterministic_repairs", []) if x.startswith("schema:"))
                for r in records
            ),
            "policy_shell_repairs": sum(
                sum(1 for x in r.get("deterministic_repairs", []) if x.startswith("policy:"))
                for r in records
            ),
            "cases_with_thinking_output": sum(
                1 for r in model_calls if (r.get("thinking_chars") or 0) > 0
            ),
            "total_thinking_chars": sum((r.get("thinking_chars") or 0) for r in model_calls),
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
            "length_exhaustions": sum(
                1 for r in model_calls if r.get("metrics", {}).get("done_reason") == "length"
            ),
        }
        s["provisional_latency_gate"] = advancement_label(s)
        summary["models"][model] = s

    summary_file = outdir / "optimization_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== SUMMARY ===")
    for model, s in summary["models"].items():
        print(
            f"{model}: {s['decisions']} | "
            f"JSON={s['valid_json_first_pass']}/{s['model_calls']} | "
            f"mean TTFC={s['mean_first_content_seconds']}s | "
            f"mean wall={s['mean_wall_seconds']}s | "
            f"think_cases={s['cases_with_thinking_output']} | "
            f"length_exhaustions={s['length_exhaustions']} | "
            f"gate={s['provisional_latency_gate']}"
        )

    print("\nSummary:", summary_file)


if __name__ == "__main__":
    main()
