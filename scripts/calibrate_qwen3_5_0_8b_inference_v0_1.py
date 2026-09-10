#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from pathlib import Path

MODEL = "qwen3.5:0.8b"

CONFIGS = [
    {
        "id": "A_default_short",
        "description": "Reproduce the original failure mode: model-native thinking, short generation budget.",
        "num_predict": 128,
        "think": None,
    },
    {
        "id": "B_default_700",
        "description": "Model-native thinking with a larger generation budget.",
        "num_predict": 700,
        "think": None,
    },
    {
        "id": "C_no_think_700",
        "description": "Thinking disabled; 700-token budget.",
        "num_predict": 700,
        "think": False,
    },
    {
        "id": "D_no_think_400",
        "description": "Thinking disabled; smaller 400-token budget for latency-first use.",
        "num_predict": 400,
        "think": False,
    },
]

PROMPTS = [
    {
        "id": "P1_json_smoke",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Return only valid JSON. Do not add markdown, commentary, or text outside JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    'Return exactly one JSON object with these keys: '
                    '"status", "model_test", "note". '
                    'Set status to "ok", model_test to "qwen3.5-0.8b", '
                    'and note to "calibration".'
                ),
            },
        ],
        "required_keys": ["status", "model_test", "note"],
    },
    {
        "id": "P2_biosafe_schema_smoke",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a biosafety assistant calibration test. "
                    "Return only valid JSON and do not make an official compliance determination."
                ),
            },
            {
                "role": "user",
                "content": (
                    'A researcher asks: "Is wearing gloves and a lab coat enough to say my experiment is safe?" '
                    "Answer conservatively. Return one JSON object with exactly these keys: "
                    '"conclusion", "missing_information", "recommended_next_step", "safety". '
                    '"missing_information" and "recommended_next_step" must be arrays. '
                    '"safety" must be an object with keys "classification", "response_mode", "reason".'
                ),
            },
        ],
        "required_keys": [
            "conclusion",
            "missing_information",
            "recommended_next_step",
            "safety",
        ],
    },
]

def detect_host():
    # Same common endpoints used by the BioSafe WSL/Ollama workflow.
    for host in ("http://localhost:11434", "http://127.0.0.1:11434"):
        try:
            with urllib.request.urlopen(host + "/api/tags", timeout=3) as r:
                if r.status == 200:
                    return host
        except Exception:
            pass
    return "http://localhost:11434"

def stream_chat(host, messages, cfg, timeout=600):
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
        "format": "json",
        "options": {
            "temperature": 0.0,
            "num_predict": cfg["num_predict"],
        },
    }
    if cfg["think"] is not None:
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
    content_parts = []
    thinking_parts = []
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

def inspect_json(content, required_keys):
    try:
        parsed = json.loads(content)
    except Exception as exc:
        return {
            "valid_json": False,
            "parse_error": str(exc),
            "has_required_keys": False,
            "parsed": None,
        }

    has_keys = isinstance(parsed, dict) and all(k in parsed for k in required_keys)
    return {
        "valid_json": True,
        "parse_error": None,
        "has_required_keys": has_keys,
        "parsed": parsed,
    }

def config_passes(records):
    return (
        len(records) == len(PROMPTS)
        and all(r["valid_json"] for r in records)
        and all(r["has_required_keys"] for r in records)
        and all((r["content"] or "").strip() for r in records)
        and all(r["done_reason"] != "length" for r in records)
    )

def choose_recommendation(by_config):
    # Prefer no-thinking configurations for BioSafe CPU use when reliability is equal.
    preference = ["D_no_think_400", "C_no_think_700", "B_default_700", "A_default_short"]
    passing = [cid for cid, rows in by_config.items() if config_passes(rows)]
    for cid in preference:
        if cid in passing:
            return cid, (
                "Recommended because it passed both calibration prompts with valid JSON, "
                "required schema keys, non-empty visible content, and no length exhaustion. "
                "No-thinking configurations are preferred for the CPU-first BioSafe baseline "
                "when reliability is equivalent."
            )
    return None, (
        "No configuration passed both prompts. Do not run the 50-case benchmark yet; "
        "upload this calibration result for diagnosis."
    )

def mean(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return round(statistics.mean(vals), 4) if vals else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=None)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument(
        "--output",
        default="output/qwen3_5_0_8b_calibration/qwen3_5_0_8b_inference_calibration_v0_1.json",
    )
    args = ap.parse_args()

    host = (args.host or detect_host()).rstrip("/")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    records = []
    by_config = {}

    print(f"BioSafe Qwen3.5-0.8B inference calibration")
    print(f"Model: {MODEL}")
    print(f"Ollama: {host}")
    print()

    for cfg in CONFIGS:
        rows = []
        print(f"=== {cfg['id']} ===")
        print(cfg["description"])

        for prompt in PROMPTS:
            print(f"  Running {prompt['id']} ...", flush=True)
            try:
                gen = stream_chat(host, prompt["messages"], cfg, timeout=args.timeout)
                check = inspect_json(gen["content"], prompt["required_keys"])
                rec = {
                    "config_id": cfg["id"],
                    "description": cfg["description"],
                    "num_predict": cfg["num_predict"],
                    "think": cfg["think"],
                    "prompt_id": prompt["id"],
                    **gen,
                    **check,
                }
            except Exception as exc:
                rec = {
                    "config_id": cfg["id"],
                    "description": cfg["description"],
                    "num_predict": cfg["num_predict"],
                    "think": cfg["think"],
                    "prompt_id": prompt["id"],
                    "content": "",
                    "thinking_chars": 0,
                    "first_event_seconds": None,
                    "first_content_seconds": None,
                    "wall_seconds": None,
                    "prompt_eval_count": 0,
                    "eval_count": 0,
                    "generation_tokens_per_second": None,
                    "done_reason": "exception",
                    "valid_json": False,
                    "parse_error": repr(exc),
                    "has_required_keys": False,
                    "parsed": None,
                }

            rows.append(rec)
            records.append(rec)
            print(
                f"    JSON={rec['valid_json']} keys={rec['has_required_keys']} "
                f"done={rec['done_reason']} think_chars={rec['thinking_chars']} "
                f"first_content={rec['first_content_seconds']}s wall={rec['wall_seconds']}s"
            )

        by_config[cfg["id"]] = rows
        print()

    recommended, rationale = choose_recommendation(by_config)

    summaries = {}
    for cfg in CONFIGS:
        cid = cfg["id"]
        rows = by_config[cid]
        summaries[cid] = {
            "passes_calibration": config_passes(rows),
            "valid_json": sum(1 for r in rows if r["valid_json"]),
            "required_keys": sum(1 for r in rows if r["has_required_keys"]),
            "length_exhaustions": sum(1 for r in rows if r["done_reason"] == "length"),
            "mean_wall_seconds": mean([r["wall_seconds"] for r in rows]),
            "mean_first_content_seconds": mean([r["first_content_seconds"] for r in rows]),
            "mean_generation_tokens_per_second": mean(
                [r["generation_tokens_per_second"] for r in rows]
            ),
            "mean_thinking_chars": mean([r["thinking_chars"] for r in rows]),
        }

    result = {
        "suite": "BioSafe_Qwen3.5_0.8B_Inference_Calibration_v0.1",
        "model": MODEL,
        "ollama_host": host,
        "purpose": (
            "Find a stable Qwen3.5-0.8B JSON-generation configuration before "
            "running the BioSafe 50-case and document benchmarks."
        ),
        "configs": CONFIGS,
        "config_summaries": summaries,
        "recommended_config": recommended,
        "recommendation_rationale": rationale,
        "records": records,
    }
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== CALIBRATION RESULT ===")
    if recommended:
        chosen = next(c for c in CONFIGS if c["id"] == recommended)
        print(f"RECOMMENDED: {recommended}")
        print(f"  think={chosen['think']}")
        print(f"  num_predict={chosen['num_predict']}")
        print("You may upload the JSON result before applying it to the benchmark runners.")
    else:
        print("NO STABLE CONFIGURATION FOUND")
        print("Do NOT run the 50-case benchmark yet.")
    print(f"Result file: {output}")

if __name__ == "__main__":
    main()
