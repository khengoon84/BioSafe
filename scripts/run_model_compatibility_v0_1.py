#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

DEFAULT_MODELS = ["qwen3:0.6b", "qwen3:1.7b", "gemma4:e2b", "gemma4:e4b"]


def http_json(url: str, payload: Dict[str, Any] | None = None, timeout: int = 60) -> Dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def check_server(host: str) -> Tuple[bool, str]:
    try:
        obj = http_json(host.rstrip("/") + "/api/tags", timeout=5)
        return True, f"{len(obj.get('models', []))} models visible"
    except Exception as exc:
        return False, str(exc)


def detect_host() -> str:
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


def model_names(host: str) -> List[str]:
    obj = http_json(host.rstrip("/") + "/api/tags", timeout=10)
    return [m.get("name", "") for m in obj.get("models", [])]


def show_model(host: str, model: str) -> Dict[str, Any]:
    try:
        return http_json(host.rstrip("/") + "/api/show", {"model": model}, timeout=30)
    except Exception as exc:
        return {"error": str(exc)}


def running_models(host: str) -> Dict[str, Any]:
    try:
        return http_json(host.rstrip("/") + "/api/ps", timeout=10)
    except Exception as exc:
        return {"error": str(exc)}


def system_snapshot() -> Dict[str, Any]:
    snap: Dict[str, Any] = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "machine": platform.machine(),
        "processor": platform.processor(),
    }
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        vals = {}
        for line in meminfo.read_text().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                vals[k] = v.strip()
        snap["wsl_mem_total"] = vals.get("MemTotal")
        snap["wsl_mem_available"] = vals.get("MemAvailable")
    return snap


def stream_chat(
    host: str,
    model: str,
    messages: List[Dict[str, str]],
    *,
    num_predict: int = 700,
    temperature: float = 0.0,
    timeout: int = 600,
    fmt: str = "json",
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "format": fmt,
        "options": {
            "temperature": temperature,
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
    prompt_eval_count = final.get("prompt_eval_count") or 0
    prompt_eval_duration = final.get("prompt_eval_duration") or 0

    return {
        "content": "".join(content_parts),
        "thinking": "".join(thinking_parts),
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


def simple_json_schema_smoke(host: str, model: str, num_predict: int) -> Dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are a test assistant. Obey the system role. "
                "Return only a JSON object with keys test and status."
            ),
        },
        {
            "role": "user",
            "content": (
                'Return {"test":"system_role_json","status":"PASS"} exactly in meaning. '
                "Do not add markdown."
            ),
        },
    ]
    try:
        result = stream_chat(
            host, model, messages,
            num_predict=num_predict,
            temperature=0.0,
            timeout=600,
            fmt="json",
        )
        parsed = json.loads(result["content"])
        semantic_pass = (
            isinstance(parsed, dict)
            and parsed.get("test") == "system_role_json"
            and str(parsed.get("status", "")).upper() == "PASS"
        )
        result["valid_json"] = True
        result["semantic_pass"] = semantic_pass
        result["parsed"] = parsed
    except Exception as exc:
        result = {
            "valid_json": False,
            "semantic_pass": False,
            "error": repr(exc),
        }
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    ap.add_argument("--host", default=None)
    ap.add_argument("--num-predict", type=int, default=128)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()

    host = (args.host or detect_host()).rstrip("/")
    ok, detail = check_server(host)
    if not ok:
        raise SystemExit(f"Ollama not reachable at {host}: {detail}")

    installed = set(model_names(host))
    report: Dict[str, Any] = {
        "suite": "BioSafe_Gemma4_Compatibility_v0.1",
        "host": host,
        "system": system_snapshot(),
        "models": [],
    }

    for model in args.models:
        rec: Dict[str, Any] = {
            "model": model,
            "installed": model in installed,
        }
        if not rec["installed"]:
            rec["status"] = "NOT_INSTALLED"
            report["models"].append(rec)
            print(f"{model}: NOT_INSTALLED")
            continue

        meta = show_model(host, model)
        rec["model_info"] = {
            "details": meta.get("details"),
            "model_info": meta.get("model_info"),
            "parameters": meta.get("parameters"),
        }

        smoke = simple_json_schema_smoke(host, model, args.num_predict)
        rec["smoke"] = smoke
        rec["running_models_after_smoke"] = running_models(host)
        rec["status"] = "PASS" if smoke.get("semantic_pass") else "FAIL"
        report["models"].append(rec)

        print(
            f"{model}: {rec['status']} | "
            f"TTFC={smoke.get('first_content_seconds')}s | "
            f"wall={smoke.get('wall_seconds')}s | "
            f"tok/s={smoke.get('generation_tokens_per_second')}"
        )

    out = Path(args.output) if args.output else ROOT / "output" / "gemma4_compatibility_v0_1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nOutput:", out)


if __name__ == "__main__":
    main()
