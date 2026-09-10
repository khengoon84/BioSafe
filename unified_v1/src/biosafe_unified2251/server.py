from pathlib import Path
import sys

from flask import Flask, jsonify, request

ROOT = Path("/home/khengoon/biosafe")
for path in (ROOT / "unified_v1/src", ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from biosafe_unified2.core import UnifiedOrchestrator
from biosafe_unified2251.service import Unified2251Service

app = Flask(__name__)
orchestrator = UnifiedOrchestrator()
service = Unified2251Service()


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "stage": "Unified-2.2.5.1 v0.1",
            "port": 8777,
            "semantic_provenance_gate": True,
            "frozen_core_modified": False,
        }
    )


@app.post("/api/ask")
def ask():
    data = request.get_json(force=True, silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Query is required."}), 400
    prepared = orchestrator.prepare(
        query, data.get("session_id"), data.get("attachments") or []
    )
    out = service.infer(prepared, data.get("documents") or [])
    if isinstance(out, dict):
        out["session_id"] = prepared["session_id"]
        # Persist the assistant answer for conversation continuity so that
        # follow-ups ("elaborate more", "I want to understand...") can bind to
        # the previous turn's subject/concept.
        orchestrator.remember_assistant(
            prepared["session_id"],
            str(out.get("conclusion") or out.get("direct_answer") or ""),
        )
    return jsonify(out)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8777, debug=False)
