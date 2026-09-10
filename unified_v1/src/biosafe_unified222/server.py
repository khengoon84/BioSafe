
from pathlib import Path
import sys
from flask import Flask,request,jsonify
ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT/"unified_v1"/"src",ROOT/"src"):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from biosafe_unified2.core import UnifiedOrchestrator
from biosafe_unified222.service import Unified222Service
app=Flask(__name__);orch=UnifiedOrchestrator();svc=Unified222Service();PORT=8771

@app.get("/health")
def health():return jsonify({"status":"ok","stage":"Unified-2.2.2 v0.1","port":PORT,
 "intent_normalization":True,"evidence_scope_enforcement":True,"frozen_core_modified":False})

@app.post("/api/ask")
def ask():
    d=request.get_json(force=True,silent=True) or {};q=(d.get("query") or "").strip()
    if not q:return jsonify({"error":"Query is required."}),400
    prep=orch.prepare(q,d.get("session_id"),d.get("attachments") or [])
    out=svc.infer(prep)
    if isinstance(out,dict):out["session_id"]=prep["session_id"]
    return jsonify(out)

@app.post("/api/plan")
def plan():
    d=request.get_json(force=True,silent=True) or {};q=(d.get("query") or "").strip()
    prep=orch.prepare(q,d.get("session_id"),d.get("attachments") or [])
    return jsonify({"intent_upstream":prep["intent"],"intent_normalized":svc.normalized_intent(prep),
                    "plan":svc.plan(prep).__dict__})

if __name__=="__main__":app.run(host="127.0.0.1",port=PORT,debug=False)
