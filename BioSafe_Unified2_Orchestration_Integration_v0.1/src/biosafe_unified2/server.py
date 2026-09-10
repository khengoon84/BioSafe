from __future__ import annotations
import json, os, urllib.request, urllib.error
from flask import Flask, request, jsonify
from biosafe_unified2 import UnifiedOrchestrator, strip_internal_metadata, dedupe_user_sections
app=Flask(__name__); orchestrator=UnifiedOrchestrator(); DOWNSTREAM=os.environ.get("BIOSAFE_UNIFIED2_DOWNSTREAM","http://127.0.0.1:8767"); PORT=int(os.environ.get("BIOSAFE_UNIFIED2_PORT","8768"))
def forward_json(path,payload,timeout=180):
    req=urllib.request.Request(DOWNSTREAM+path,data=json.dumps(payload).encode(),method="POST",headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:return r.getcode(),json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw=e.read().decode(errors="replace")
        try:data=json.loads(raw)
        except Exception:data={"error":raw or str(e)}
        return e.code,data
    except Exception as e:return 502,{"error":f"Downstream unavailable: {e}","downstream":DOWNSTREAM}
@app.get("/health")
def health(): return jsonify({"status":"ok","architecture":"Unified Ask BioSafe v1","stage":"Unified-2 v0.1","downstream":DOWNSTREAM,"port":PORT,"sessions":len(orchestrator.sessions),"frozen_core_modified":False,"constitution_runtime_mode":"separate-policy-object-not-query-prefixed"})
@app.post("/api/ask")
def ask():
    data=request.get_json(force=True,silent=True) or {}; query=(data.get("query") or "").strip()
    if not query:return jsonify({"error":"Query is required."}),400
    prep=orchestrator.prepare(query,data.get("session_id"),data.get("attachments") or [])
    if prep["missing_information"] and prep["intent"]=="form_e_assist": return jsonify({"session_id":prep["session_id"],"direct_answer":"I need a small amount of project information before I can assist reliably.","what_i_need_from_you":[{"question":x["question"],"why":x["why"]} for x in prep["missing_information"]],"_unified2":prep}),200
    path="/api/form-e" if prep["workflow"]=="form-e" else "/api/ask"; status,payload=forward_json(path,{"query":prep["query"],"session_id":prep["session_id"]}); visible=strip_internal_metadata(payload)
    if isinstance(visible,dict): visible=dedupe_user_sections(visible); visible["session_id"]=prep["session_id"]; visible["_unified2"]=prep
    return jsonify(visible),status
@app.post("/api/session/reset")
def reset():
    data=request.get_json(force=True,silent=True) or {}; sid=(data.get("session_id") or "").strip(); local=orchestrator.reset(sid) if sid else False; ds_status,ds=forward_json("/api/session/reset",{"session_id":sid},30) if sid else (200,{"reset":False})
    return jsonify({"session_id":sid,"reset":bool(local or ds.get("reset")),"local_reset":local,"downstream_reset":ds.get("reset",False)}),200 if ds_status<500 else ds_status
if __name__=="__main__": app.run(host="127.0.0.1",port=PORT,debug=False)
