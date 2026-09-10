#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from run_model_compatibility_v0_1 import check_server, detect_host, model_names
from run_inference_mode_optimization_v0_1 import MODEL_CONFIGS, stream_chat_custom


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["gemma4:e2b", "gemma4:e4b"])
    ap.add_argument("--host", default=None)
    args = ap.parse_args()

    host = (args.host or detect_host()).rstrip("/")
    ok, detail = check_server(host)
    if not ok:
        raise SystemExit(f"Ollama not reachable at {host}: {detail}")

    installed = set(model_names(host))
    out = {
        "suite": "BioSafe_Gemma4_NoThinking_Smoke_v0.1",
        "host": host,
        "models": [],
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are a BioSafe inference test. "
                "Return one JSON object only. Do not explain your reasoning."
            ),
        },
        {
            "role": "user",
            "content": (
                'Return {"status":"PASS","mode":"no-thinking"} exactly in meaning.'
            ),
        },
    ]

    for model in args.models:
        rec = {"model": model}
        if model not in installed:
            rec["status"] = "NOT_INSTALLED"
            out["models"].append(rec)
            continue

        cfg = dict(MODEL_CONFIGS[model])
        cfg["num_predict"] = 80
        try:
            gen = stream_chat_custom(host, model, messages, cfg, timeout=600)
            try:
                parsed = json.loads(gen["content"])
                valid_json = True
            except Exception as exc:
                parsed = None
                valid_json = False
                rec["parse_error"] = str(exc)

            rec.update({
                "status": "PASS" if valid_json else "FAIL",
                "valid_json": valid_json,
                "parsed": parsed,
                "thinking_chars": gen["thinking_chars"],
                "first_content_seconds": gen["first_content_seconds"],
                "wall_seconds": gen["wall_seconds"],
                "done_reason": gen["done_reason"],
                "eval_count": gen["eval_count"],
                "generation_tokens_per_second": gen["generation_tokens_per_second"],
            })
        except Exception as exc:
            rec.update({"status": "FAIL", "error": repr(exc)})

        out["models"].append(rec)
        print(
            f"{model}: {rec['status']} | JSON={rec.get('valid_json')} | "
            f"thinking_chars={rec.get('thinking_chars')} | "
            f"TTFC={rec.get('first_content_seconds')}s | wall={rec.get('wall_seconds')}s"
        )

    path = ROOT / "output" / "gemma4_nothinking_smoke_v0_1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nOutput:", path)


if __name__ == "__main__":
    main()
