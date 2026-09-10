
from __future__ import annotations
import sys
from pathlib import Path
from flask import Flask, request, jsonify

ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT/"unified_v1"/"src", ROOT/"src"):
    if str(p) not in sys.path: sys.path.insert(0,str(p))

from biosafe_unified2.core import UnifiedOrchestrator, strip_internal_metadata, dedupe_user_sections
from biosafe_unified22.service import BioSafeConstitutionAwareInferenceServiceV01

app=Flask(__name__)
orchestrator=UnifiedOrchestrator()
engine=BioSafeConstitutionAwareInferenceServiceV01(ROOT)
PORT=8769

def visible(payload):
    p=strip_internal_metadata(payload)
    return dedupe_user_sections(p) if isinstance(p,dict) else p

@app.get("/health")
def health():
    return jsonify({
        "status":"ok",
        "architecture":"Unified Ask BioSafe v1",
        "stage":"Unified-2.2 v0.1",
        "port":PORT,
        "constitution_aware_generation":True,
        "retrieval_query_contaminated":False,
        "frozen_core_modified":False,
    })

@app.post("/api/ask")
def ask():
    data=request.get_json(force=True,silent=True) or {}
    query=(data.get("query") or "").strip()
    if not query:return jsonify({"error":"Query is required."}),400
    prep=orchestrator.prepare(query,data.get("session_id"),data.get("attachments") or [])

    # Preserve Unified-2.1 deterministic elicitation for Form E.
    if prep["missing_information"] and prep["intent"]=="form_e_assist":
        return jsonify({
            "session_id":prep["session_id"],
            "direct_answer":"I need a small amount of project information before I can assist reliably.",
            "what_i_need_from_you":[{"question":x["question"],"why":x["why"]} for x in prep["missing_information"]],
            "_unified2":prep,
        }),200

    workflow={"review":"document_review","form-e":"form_e"}.get(prep["workflow"],"ask")
    result=engine.infer(
        query,
        documents=[],
        workflow=workflow,
        interaction_context={
            "intent":prep["intent"],
            "case_state":prep["case_state"],
            "resolved_reference":prep["resolved_reference"],
            "attachments_present":bool(prep["attachments"]),
        }
    )
    if isinstance(result,dict):
        result["session_id"]=prep["session_id"]
        result["_unified2"]=prep
    return jsonify(result),200

@app.post("/api/session/reset")
def reset():
    data=request.get_json(force=True,silent=True) or {}
    sid=(data.get("session_id") or "").strip()
    return jsonify({"session_id":sid,"reset":orchestrator.reset(sid) if sid else False})

if __name__=="__main__":
    app.run(host="127.0.0.1",port=PORT,debug=False)
