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
from biosafe_pipeline_v0_3_1 import BioSafePipelineV031
from output_validator_v0_2 import validate_output, build_retry_instruction
from boundary_validator_v0_3_1 import validate_boundaries

TARGET_IDS = [
    "BS-005","BS-007","MY-002","MY-006","MY-007","MY-008",
    "TR-001","TR-004","PROP-004","FORM-002","FORM-004","SAFE-001","SAFE-002"
]


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

    models = installed_models(host)
    if args.model not in models:
        raise SystemExit(f"{args.model} not installed in Ollama")

    pipe = BioSafePipelineV031(ROOT, 3)
    all_cases = load_benchmark(ROOT / "data/BioSafe_Benchmark_Dataset_v0.1.jsonl")
    by_id = {c["id"]: c for c in all_cases}
    cases = [by_id[x] for x in TARGET_IDS if x in by_id]

    safe_model = args.model.replace(":","_").replace("/","_")
    out = ROOT / "output" / f"boundary_v0_3_1_{safe_model}.jsonl"
    out.parent.mkdir(exist_ok=True)

    stats = {
        "total": 0,
        "deterministic_short_circuit": 0,
        "model_calls": 0,
        "retries": 0,
        "retry_improved": 0,
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
            policy = bundle["policy_decision"]

            rec = {
                "case_id": case["id"],
                "model_id": args.model,
                "policy_decision": policy,
                "route": bundle["route"],
                "evidence_ids": [x["evidence_id"] for x in bundle["evidence_bundle"]],
            }

            if deterministic is not None:
                stats["deterministic_short_circuit"] += 1
                core = validate_output(deterministic, bundle, valid_json=True)
                boundary = validate_boundaries(deterministic, policy)
                final = merged_decision(core, boundary)
                rec.update({
                    "generation_mode": "deterministic_short_circuit",
                    "model_called": False,
                    "parsed_output": deterministic,
                    "core_validation": core.to_dict(),
                    "boundary_validation": boundary.to_dict(),
                    "final_decision": final,
                    "latency_seconds": 0.0,
                })
            else:
                stats["model_calls"] += 1
                st = time.perf_counter()
                obj = ollama_chat(host, args.model, messages, 0.0, 700, 600)
                latency = time.perf_counter() - st
                content = obj.get("message", {}).get("content", "")
                parsed, valid_json, err = parse_json(content)
                core = validate_output(parsed, bundle, valid_json=valid_json)
                boundary = validate_boundaries(parsed or {}, policy)
                first = merged_decision(core, boundary)

                rec["first_attempt"] = {
                    "latency_seconds": round(latency, 4),
                    "valid_json": valid_json,
                    "raw_output": content,
                    "parsed_output": parsed,
                    "parse_error": err,
                    "core_validation": core.to_dict(),
                    "boundary_validation": boundary.to_dict(),
                    "decision": first,
                }

                final_parsed = parsed
                final_core = core
                final_boundary = boundary
                final = first
                total_latency = latency

                if not args.no_retry and first == "RETRY":
                    stats["retries"] += 1
                    retry_issues = list(core.issues) + list(boundary.issues)
                    retry_stub = type("RetryStub", (), {"issues": retry_issues})()
                    retry_messages = list(messages) + [
                        {"role":"assistant","content":content},
                        {"role":"user","content":
                            build_retry_instruction(retry_stub)
                            + "\nAdditional BioSafe boundary issues:\n"
                            + "\n".join(f"- {x}" for x in boundary.issues)
                            + "\nRe-read and obey every policy_decision constraint."
                            + "\nA later caveat does not repair an earlier prohibited conclusion."
                            + "\nReturn one corrected JSON object only."
                        }
                    ]

                    st2 = time.perf_counter()
                    obj2 = ollama_chat(host, args.model, retry_messages, 0.0, 700, 600)
                    latency2 = time.perf_counter() - st2
                    total_latency += latency2
                    content2 = obj2.get("message", {}).get("content", "")
                    parsed2, valid2, err2 = parse_json(content2)
                    core2 = validate_output(parsed2, bundle, valid_json=valid2)
                    boundary2 = validate_boundaries(parsed2 or {}, policy)
                    final2 = merged_decision(core2, boundary2)

                    if first == "RETRY" and final2 in ("PASS", "PASS_WITH_WARNING"):
                        stats["retry_improved"] += 1

                    rec["retry_attempt"] = {
                        "latency_seconds": round(latency2, 4),
                        "valid_json": valid2,
                        "raw_output": content2,
                        "parsed_output": parsed2,
                        "parse_error": err2,
                        "core_validation": core2.to_dict(),
                        "boundary_validation": boundary2.to_dict(),
                        "decision": final2,
                    }
                    final_parsed, final_core, final_boundary, final = (
                        parsed2, core2, boundary2, final2
                    )

                rec.update({
                    "generation_mode": "model",
                    "model_called": True,
                    "parsed_output": final_parsed,
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
                f"mode={rec['generation_mode']} | "
                f"policy={policy['mode']}"
            )

    print("\nOutput:", out)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
