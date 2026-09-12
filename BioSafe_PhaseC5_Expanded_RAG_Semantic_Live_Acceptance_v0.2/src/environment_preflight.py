from __future__ import annotations

import json
import socket
import urllib.request
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parents[1]
EXPECTED_MODELS={
    "qwen3.5:0.8b":"f3817196d142eaf72ce79dfebe53dcb20bd21da87ce13e138a8f8e10a866b3a4",
    "qwen3.5:2b":"324d162be6ca5629ae4517c8710434d0bd2d665bc94dbad46e9af8fbf8a2f0df",
}


def _get(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=3) as response:
        return json.loads(response.read().decode())


def _port_available(port: int) -> bool:
    with socket.socket() as sock:
        sock.settimeout(1)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def evaluate() -> dict[str, Any]:
    errors=[]; version=None; tags={}
    try:
        version=_get("http://127.0.0.1:11434/api/version").get("version")
        tags={m.get("name"):m for m in _get("http://127.0.0.1:11434/api/tags").get("models",[])}
    except Exception as exc:
        errors.append(f"ollama_unavailable:{type(exc).__name__}")
    models={name:{"present":name in tags,"digest":tags.get(name,{}).get("digest")} for name in EXPECTED_MODELS}
    for name,digest in EXPECTED_MODELS.items():
        if name in tags and tags[name].get("digest") != digest: errors.append(f"model_digest_mismatch:{name}")
    ports={str(port):_port_available(port) for port in (8777,8779)}
    if not ports["8779"]: errors.append("candidate_port_8779_in_use")
    return {
        "artifact_version":"BioSafe_Phase5_Environment_Preflight_v0.1",
        "ollama_endpoint":"http://127.0.0.1:11434",
        "ollama_version":version,
        "models":models,
        "ports_available":ports,
        "candidate_service_inference_enabled":True,
        "result":"READY_FOR_C5_LIVE_SERVICE_PREFLIGHT" if not errors else "BLOCKED_ENVIRONMENT_NOT_VALIDATED",
        "errors":errors,
        "live_execution_performed":False,
        "claim_use_status":"REVIEW_REQUIRED_BEFORE_CLAIM_USE",
        "live_activation_status":"PROHIBITED_PENDING_PHASE_C_GATES",
        "reason":"The additive candidate inference bridge is implemented, but live semantic acceptance still requires candidate-service launch, baseline-service verification, and complete semantic/provenance review.",
    }