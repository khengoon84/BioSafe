
from __future__ import annotations
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from service import BioSafeLocalService

app = Flask(__name__)
service = BioSafeLocalService()

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/ask")
def ask():
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Query is required."}), 400
    return jsonify(service.run_query(query))

@app.post("/api/review")
def review():
    query = (request.form.get("query") or "Review this document for biosafety and regulatory gaps.").strip()
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Document file is required."}), 400

    text = f.read().decode("utf-8", errors="replace")
    composite = f"{query}\n\nUSER DOCUMENT:\n{text}"
    result = service.run_query(composite)
    result["_document"] = {"filename": f.filename, "chars": len(text)}
    return jsonify(result)

@app.post("/api/form-e")
def form_e():
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Form E description is required."}), 400
    composite = (
        "Assist with Malaysian Form E using only supported information. "
        "Do not fabricate missing fields or simulate IBC determination.\n\n"
        + query
    )
    return jsonify(service.run_query(composite))

@app.get("/health")
def health():
    return jsonify({"status": "ok", "stage": "9", "shell": "v0.1"})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False)
