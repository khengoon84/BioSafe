from __future__ import annotations
import sys
from pathlib import Path
from flask import Flask, jsonify, request

ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT/"cra_v1"/"src",ROOT/"src"):
    if str(p) not in sys.path:
        sys.path.insert(0,str(p))

from cra_service_runtime_v0_1 import CRAServiceRuntimeV01

def create_app(runtime=None):
    app=Flask(__name__)
    rt=runtime or CRAServiceRuntimeV01()
    app.config["CRA_RUNTIME"]=rt

    @app.get("/health")
    def health():
        return jsonify({
            "status":"ok","architecture":"CRA-v1","bridge":"CRA-8.2-v0.1",
            "port":8766,"live_ui_modified":False,"sessions":rt.sessions.count()
        })

    @app.post("/api/ask")
    def ask():
        data=request.get_json(force=True,silent=True) or {}
        query=(data.get("query") or "").strip()
        if not query:
            return jsonify({"error":"Query is required."}),400
        try:
            return jsonify(rt.handle(query,workflow="ask",session_id=data.get("session_id")))
        except Exception as e:
            return jsonify({"error":str(e),"bridge":"CRA-8.2-v0.1"}),500

    @app.post("/api/review")
    def review():
        query=(request.form.get("query") or "Review this document for biosafety and regulatory gaps.").strip()
        f=request.files.get("file")
        if not f:
            return jsonify({"error":"Document file is required."}),400
        text=f.read().decode("utf-8",errors="replace")
        documents=[{"filename":f.filename or "upload.txt","text":text}]
        try:
            result=rt.handle(
                query,workflow="review",documents=documents,
                session_id=request.form.get("session_id")
            )
            result["_document"]={"filename":f.filename,"chars":len(text)}
            return jsonify(result)
        except Exception as e:
            return jsonify({"error":str(e),"bridge":"CRA-8.2-v0.1"}),500

    @app.post("/api/form-e")
    def form_e():
        data=request.get_json(force=True,silent=True) or {}
        query=(data.get("query") or "").strip()
        if not query:
            return jsonify({"error":"Form E description is required."}),400
        try:
            return jsonify(rt.handle(query,workflow="form-e",session_id=data.get("session_id")))
        except Exception as e:
            return jsonify({"error":str(e),"bridge":"CRA-8.2-v0.1"}),500

    @app.post("/api/session/reset")
    def reset_session():
        data=request.get_json(force=True,silent=True) or {}
        sid=(data.get("session_id") or "").strip()
        if not sid:
            return jsonify({"error":"session_id is required."}),400
        return jsonify({"session_id":sid,"reset":rt.sessions.reset(sid)})
    return app

if __name__=="__main__":
    create_app().run(host="127.0.0.1",port=8766,debug=False)
