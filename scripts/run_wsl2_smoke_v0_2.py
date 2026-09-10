#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from run_biosafe_ollama import check_server, installed_models, ollama_chat
from biosafe_pipeline_v0_1 import BioSafePipelineV01, load_benchmark
from output_validator_v0_2 import validate_output, build_retry_instruction


def detect_host():
    env = os.getenv("BIOSAFE_OLLAMA_HOST")
    if env and env.upper() != "AUTO":
        return env.rstrip("/")

    candidates = ["http://127.0.0.1:11434"]

    try:
        gw = subprocess.check_output(
            ["sh", "-lc", "ip route | awk '/default/ {print $3; exit}'"],
            text=True,
        ).strip()
        if gw:
            candidates.append(f"http://{gw}:11434")
    except Exception:
        pass

    for host in candidates:
        ok, _ = check_server(host)
        if ok:
            return host

    return candidates[0]


def parse_json(content: str):
    try:
        return json.loads(content), True, None
    except Exception as exc:
        return None, False, str(exc)


def generation_record(obj, latency, content):
    return {
        "latency_seconds": round(latency, 4),
        "raw_output": content,
        "ollama_metrics": {
            "total_duration": obj.get("total_duration"),
            "load_duration": obj.get("load_duration"),
            "prompt_eval_count": obj.get("prompt_eval_count"),
            "eval_count": obj.get("eval_count"),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--model",
        default=os.getenv("BIOSAFE_OLLAMA_MODEL", "qwen3:0.6b"),
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=int(os.getenv("BIOSAFE_BENCHMARK_LIMIT", "5")),
    )
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--host", default=None)
    ap.add_argument("--no-retry", action="store_true")
    args = ap.parse_args()

    host = (args.host or detect_host()).rstrip("/")
    ok, _detail = check_server(host)
    if not ok:
        print(f"ERROR: Ollama not reachable at {host}")
        print("Run: python3 scripts/detect_ollama.py")
        raise SystemExit(2)

    models = installed_models(host)
    if args.model not in models:
        print(f"ERROR: {args.model} is not installed in Ollama.")
        print(f"On Windows, run: ollama pull {args.model}")
        raise SystemExit(3)

    pipe = BioSafePipelineV01(ROOT, 3)
    cases = load_benchmark(ROOT / "data/BioSafe_Benchmark_Dataset_v0.1.jsonl")
    cases = cases[args.start : args.start + args.limit]

    safe = args.model.replace(":", "_").replace("/", "_")
    out = (
        ROOT
        / "output"
        / f"wsl2_validator_v0_2_{safe}_{args.start}_{args.start + len(cases) - 1}.jsonl"
    )
    out.parent.mkdir(exist_ok=True)

    print("Ollama:", host)
    print("Model:", args.model)
    print("Cases:", len(cases))
    print("Validator: v0.2")
    print("One retry:", "OFF" if args.no_retry else "ON")
    print("Output:", out)

    summary = {
        "PASS": 0,
        "PASS_WITH_WARNING": 0,
        "RETRY": 0,
        "HARD_FAIL": 0,
        "retried": 0,
        "retry_improved": 0,
    }

    with out.open("w", encoding="utf-8") as f:
        for i, case in enumerate(cases, 1):
            rec = {
                "case_id": case["id"],
                "model_id": args.model,
                "ollama_host": host,
            }

            try:
                bundle, messages = pipe.build_messages(
                    case["user_input"],
                    case["id"],
                    case["safety_class"],
                )
                rec["route"] = bundle["route"]
                rec["evidence_ids"] = [
                    x["evidence_id"] for x in bundle["evidence_bundle"]
                ]

                # First generation
                st = time.perf_counter()
                obj = ollama_chat(host, args.model, messages, 0.0, 700, 600)
                latency = time.perf_counter() - st
                content = obj.get("message", {}).get("content", "")
                parsed, valid_json, parse_error = parse_json(content)

                first = generation_record(obj, latency, content)
                first["valid_json"] = valid_json
                if valid_json:
                    first["parsed_output"] = parsed
                else:
                    first["parse_error"] = parse_error

                validation = validate_output(
                    parsed,
                    bundle,
                    valid_json=valid_json,
                )
                first["validation"] = validation.to_dict()
                rec["first_attempt"] = first

                final_parsed = parsed
                final_valid = valid_json
                final_validation = validation
                final_content = content

                # One constrained retry for fixable validation failures.
                if (
                    not args.no_retry
                    and validation.decision == "RETRY"
                ):
                    summary["retried"] += 1

                    retry_messages = list(messages)
                    retry_messages.append(
                        {"role": "assistant", "content": content}
                    )
                    retry_messages.append(
                        {
                            "role": "user",
                            "content": build_retry_instruction(validation),
                        }
                    )

                    st2 = time.perf_counter()
                    obj2 = ollama_chat(
                        host,
                        args.model,
                        retry_messages,
                        0.0,
                        700,
                        600,
                    )
                    latency2 = time.perf_counter() - st2
                    content2 = obj2.get("message", {}).get("content", "")
                    parsed2, valid_json2, parse_error2 = parse_json(content2)

                    retry_rec = generation_record(obj2, latency2, content2)
                    retry_rec["valid_json"] = valid_json2
                    if valid_json2:
                        retry_rec["parsed_output"] = parsed2
                    else:
                        retry_rec["parse_error"] = parse_error2

                    validation2 = validate_output(
                        parsed2,
                        bundle,
                        valid_json=valid_json2,
                    )
                    retry_rec["validation"] = validation2.to_dict()
                    rec["retry_attempt"] = retry_rec

                    final_parsed = parsed2
                    final_valid = valid_json2
                    final_validation = validation2
                    final_content = content2

                    if validation2.decision in {"PASS", "PASS_WITH_WARNING"}:
                        summary["retry_improved"] += 1

                rec["valid_json"] = final_valid
                rec["parsed_output"] = final_parsed
                rec["raw_output"] = final_content
                rec["validation"] = final_validation.to_dict()
                rec["final_decision"] = final_validation.decision

                summary[final_validation.decision] += 1

                print(
                    f"[{i:02d}/{len(cases):02d}] {case['id']}: "
                    f"{final_validation.decision} "
                    f"(first={validation.decision}, {latency:.1f}s)"
                )

            except Exception as exc:
                rec["generation_error"] = repr(exc)
                rec["valid_json"] = False
                rec["final_decision"] = "HARD_FAIL"
                rec["validation"] = {
                    "decision": "HARD_FAIL",
                    "issues": [f"runtime:{repr(exc)}"],
                    "warnings": [],
                    "checks": {},
                }
                summary["HARD_FAIL"] += 1
                print(f"[{i:02d}/{len(cases):02d}] {case['id']}: ERROR {exc}")

            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()

    print("\nDone:", out)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
