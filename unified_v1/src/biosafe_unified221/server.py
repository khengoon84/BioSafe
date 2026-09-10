
from pathlib import Path
import sys
from flask import Flask,request,jsonify
ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT/"unified_v1"/"src",ROOT/"src"):
    if str(p) not in sys.path: sys.path.insert(0,str(p))
from biosafe_unified2.core import UnifiedOrchestrator
from biosafe_unified221.service import Unified221Service

app=Flask(__name__)
orch=UnifiedOrchestrator()
svc=Unified221Service()
PORT=8770

@app.get("/health")
def health():
    return jsonify({
        "status":"ok","stage":"Unified-2.2.1 v0.1",
        "architecture":"Evidence Requirement Planner + Constitution-Aware Generation",
        "port":PORT,"frozen_core_modified":False
    })

@app.post("/api/plan")
def plan():
    d=request.get_json(force=True,silent=True) or {}
    q=(d.get("query") or "").strip()
    if not q:return jsonify({"error":"Query is required."}),400
    prep=orch.prepare(q,d.get("session_id"),d.get("attachments") or [])
    p=svc.plan(prep)
    return jsonify({"session_id":prep["session_id"],"intent":prep["intent"],"plan":p.__dict__})

@app.post("/api/ask")
def ask():
    d=request.get_json(force=True,silent=True) or {}
    q=(d.get("query") or "").strip()
    if not q:return jsonify({"error":"Query is required."}),400
    prep=orch.prepare(q,d.get("session_id"),d.get("attachments") or [])
    if prep["missing_information"] and prep["intent"]=="form_e_assist":
        return jsonify({
            "session_id":prep["session_id"],
            "direct_answer":"I need a small amount of project information before I can assist reliably.",
            "what_i_need_from_you":[{"question":x["question"],"why":x["why"]} for x in prep["missing_information"]]
        })
    out=svc.infer_with_plan(prep)
    if isinstance(out,dict): out["session_id"]=prep["session_id"]
    return jsonify(out)

@app.post("/api/session/reset")
def reset():
    d=request.get_json(force=True,silent=True) or {}
    sid=(d.get("session_id") or "").strip()
    return jsonify({"session_id":sid,"reset":orch.reset(sid) if sid else False})

if __name__=="__main__":
    app.run(host="127.0.0.1",port=PORT,debug=False)
