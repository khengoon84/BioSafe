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
from biosafe_pipeline_v0_1 import load_benchmark
from biosafe_pipeline_v0_3_2 import BioSafePipelineV032
from output_validator_v0_2 import validate_output, build_retry_instruction
from boundary_validator_v0_3_2 import validate_boundaries
from output_normalizer_v0_3_2 import normalize_output
from policy_shell_enforcer_v0_3_2 import enforce_policy_shell

TARGET_IDS = ["BS-005","BS-007","PROP-004","FORM-002","FORM-004"]


def detect_host():
    env = os.getenv("BIOSAFE_OLLAMA_HOST")
    if env and env.upper() != "AUTO":
        return env.rstrip("/")
    candidates = ["http://127.0.0.1:11434"]
    try:
        gw = subprocess.check_output(
            ["sh","-lc","ip route | awk '/default/ {print $3; exit}'"],
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


def process_parsed(parsed, bundle):
    repairs = []
    if isinstance(parsed, dict):
        parsed, r1 = normalize_output(parsed)
        repairs.extend(r1)
        parsed, r2 = enforce_policy_shell(parsed, bundle["policy_decision"])
        repairs.extend(r2)

    core = validate_output(parsed, bundle, valid_json=isinstance(parsed, dict))
    boundary = validate_boundaries(parsed or {}, bundle["policy_decision"])
    return parsed, repairs, core, boundary, merged_decision(core, boundary)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:0.6b")
    ap.add_argument("--host", default=None)
    ap.add_argument("--no-retry", action="store_true")
    args = ap.parse_args()

    host = (args.host or detect_host()).rstrip("/")
    ok, _ = check_server(host)
    if not ok:
        raise SystemExit(f"Ollama not reachable at {host}")

    if args.model not in installed_models(host):
        raise SystemExit(f"{args.model} not installed in Ollama")

    pipe = BioSafePipelineV032(ROOT, 3)
    cases_all = load_benchmark(ROOT / "data/BioSafe_Benchmark_Dataset_v0.1.jsonl")
    by_id = {c["id"]: c for c in cases_all}
    cases = [by_id[x] for x in TARGET_IDS]

    safe_model = args.model.replace(":","_").replace("/","_")
    out = ROOT / "output" / f"boundary_v0_3_2_{safe_model}.jsonl"
    out.parent.mkdir(exist_ok=True)

    stats = {
        "total": 0,
        "model_calls": 0,
        "retries": 0,
        "deterministic_repairs": 0,
        "PASS": 0,
        "PASS_WITH_WARNING": 0,
        "RETRY": 0,
        "HARD_FAIL": 0,
    }

    with out.open("w", encoding="utf-8") as f:
        for case in cases:
            stats["total"] += 1
            bundle, messages, deterministic = pipe.build_messages(
                case["user_input"], case["id"], case["safety_class"]
            )

            rec = {
                "case_id": case["id"],
                "model_id": args.model,
                "policy_decision": bundle["policy_decision"],
                "route": bundle["route"],
                "evidence_ids": [x["evidence_id"] for x in bundle["evidence_bundle"]],
            }

            if deterministic is not None:
                parsed, repairs, core, boundary, final = process_parsed(deterministic, bundle)
                rec.update({
                    "generation_mode": "deterministic_short_circuit",
                    "model_called": False,
                    "parsed_output": parsed,
                    "deterministic_repairs": repairs,
                    "core_validation": core.to_dict(),
                    "boundary_validation": boundary.to_dict(),
                    "final_decision": final,
                    "latency_seconds": 0.0,
                })
            else:
                stats["model_calls"] += 1
                st = time.perf_counter()
                obj = ollama_chat(host, args.model, messages, 0.0, 700, 600)
                latency1 = time.perf_counter() - st
                raw1 = obj.get("message", {}).get("content", "")
                parsed1, valid1, err1 = parse_json(raw1)

                if valid1:
                    parsed1, repairs1, core1, boundary1, first = process_parsed(parsed1, bundle)
                else:
                    repairs1 = []
                    core1 = validate_output(None, bundle, valid_json=False)
                    boundary1 = validate_boundaries({}, bundle["policy_decision"])
                    first = merged_decision(core1, boundary1)

                stats["deterministic_repairs"] += len(repairs1)

                rec["first_attempt"] = {
                    "latency_seconds": round(latency1, 4),
                    "valid_json": valid1,
                    "raw_output": raw1,
                    "parse_error": err1,
                    "parsed_output_after_repairs": parsed1,
                    "deterministic_repairs": repairs1,
                    "core_validation": core1.to_dict(),
                    "boundary_validation": boundary1.to_dict(),
                    "decision": first,
                }

                final_parsed = parsed1
                final_repairs = repairs1
                final_core = core1
                final_boundary = boundary1
                final = first
                total_latency = latency1

                if not args.no_retry and first == "RETRY":
                    stats["retries"] += 1
                    retry_issues = list(core1.issues) + list(boundary1.issues)
                    retry_stub = type("RetryStub", (), {"issues": retry_issues})()
                    retry_messages = list(messages) + [
                        {"role":"assistant","content":raw1},
                        {"role":"user","content":
                            build_retry_instruction(retry_stub)
                            + "\nAdditional BioSafe boundary issues:\n"
                            + "\n".join(f"- {x}" for x in boundary1.issues)
                            + "\nReturn one corrected JSON object only."
                        }
                    ]
                    st2 = time.perf_counter()
                    obj2 = ollama_chat(host, args.model, retry_messages, 0.0, 700, 600)
                    latency2 = time.perf_counter() - st2
                    total_latency += latency2
                    raw2 = obj2.get("message", {}).get("content", "")
                    parsed2, valid2, err2 = parse_json(raw2)

                    if valid2:
                        parsed2, repairs2, core2, boundary2, second = process_parsed(parsed2, bundle)
                    else:
                        repairs2 = []
                        core2 = validate_output(None, bundle, valid_json=False)
                        boundary2 = validate_boundaries({}, bundle["policy_decision"])
                        second = merged_decision(core2, boundary2)

                    stats["deterministic_repairs"] += len(repairs2)

                    rec["retry_attempt"] = {
                        "latency_seconds": round(latency2, 4),
                        "valid_json": valid2,
                        "raw_output": raw2,
                        "parse_error": err2,
                        "parsed_output_after_repairs": parsed2,
                        "deterministic_repairs": repairs2,
                        "core_validation": core2.to_dict(),
                        "boundary_validation": boundary2.to_dict(),
                        "decision": second,
                    }
                    final_parsed = parsed2
                    final_repairs = repairs1 + repairs2
                    final_core = core2
                    final_boundary = boundary2
                    final = second

                rec.update({
                    "generation_mode": "model",
                    "model_called": True,
                    "parsed_output": final_parsed,
                    "deterministic_repairs": final_repairs,
                    "core_validation": final_core.to_dict(),
                    "boundary_validation": final_boundary.to_dict(),
                    "final_decision": final,
                    "latency_seconds": round(total_latency, 4),
                })

            stats[rec["final_decision"]] += 1
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(
                f"{case['id']}: {rec['final_decision']} | "
                f"repairs={len(rec.get('deterministic_repairs', []))} | "
                f"latency={rec['latency_seconds']}s"
            )

    print("\nOutput:", out)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
