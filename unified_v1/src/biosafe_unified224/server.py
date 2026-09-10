from pathlib import Path
import sys
from flask import Flask,request,jsonify
R=Path("/home/khengoon/biosafe")
for p in (R/"unified_v1/src",R/"src"):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
from biosafe_unified2.core import UnifiedOrchestrator
from biosafe_unified224.service import Unified224Service
app=Flask(__name__);orch=UnifiedOrchestrator();svc=Unified224Service()
@app.get("/health")
def health():return jsonify({"status":"ok","stage":"Unified-2.2.4 v0.1","port":8773,"frozen_core_modified":False})
@app.post("/api/ask")
def ask():
 d=request.get_json(force=True,silent=True) or {};q=(d.get("query") or "").strip()
 if not q:return jsonify({"error":"Query is required."}),400
 prep=orch.prepare(q,d.get("session_id"),d.get("attachments") or [])
 out=svc.infer(prep,d.get("documents") or [])
 if isinstance(out,dict):out["session_id"]=prep["session_id"]
 return jsonify(out)
if __name__=="__main__":app.run(host="127.0.0.1",port=8773,debug=False)
