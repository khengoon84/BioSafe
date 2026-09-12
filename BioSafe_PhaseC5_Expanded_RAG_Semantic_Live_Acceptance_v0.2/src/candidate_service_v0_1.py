from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
sys.path.insert(0,str(HERE.parents[0]/"unified_v1/src"))
sys.path.insert(0,str(HERE.parents[0]/"src"))
from c5_bridge import ACTIVE_KB, ACTIVE_MANIFEST, C37_GOLD, load, run_path, validate_hashes
from candidate_inference_service_v0_1 import CandidateInferenceServiceV01
from phase_c3_7 import C37CFG02, build_artifacts, retrieval_policy
from retriever_cfg02_base import BioSafeCFG02
from biosafe_unified2.core import UnifiedOrchestrator
from authorization_evidence_readiness_v0_1 import evaluate_evidence_readiness


class CandidateRetrievalService:
    def __init__(self):
        self.active=load(ACTIVE_KB); self.manifest=load(ACTIVE_MANIFEST)
        self.candidate,self.candidate_manifest,_=build_artifacts(); self.policy=retrieval_policy()
        self.cases=[c for c in load(C37_GOLD)["cases"] if c["case_type"] not in {"unknown_evidence","currentness","conflict"} and not c["case_id"].startswith("C37-F-")]
        self.inference=None

    def health(self) -> dict[str,Any]:
        return {"status":"ok","stage":"BioSafe C5 candidate inference v0.1","candidate":"C37_METADATA_CFG02:metadata_off","candidate_evidence_origin":"C5_REVIEWED_CANDIDATE","control_path":"ACTIVE_KB_V0.2_FROZEN_PATH","frozen_core_modified":False,"active_kb_modified":False,"claim_use_status":"REVIEW_REQUIRED_BEFORE_CLAIM_USE","live_activation_status":"PROHIBITED_PENDING_PHASE_C_GATES","inference_enabled":True,"ollama_call_enabled":True,"evaluation_only_serialized_service":True,"hash_errors":validate_hashes(),"authorization_evidence_readiness":evaluate_evidence_readiness(self.candidate.get("claims",[]))}

    def inspect(self, query: str) -> dict[str,Any]:
        case={"case_id":"C5-ADHOC","query":query,"acceptable_claim_ids":[]}
        baseline=run_path(BioSafeCFG02,self.active,self.manifest,self.policy,[case],"ACTIVE_KB_V0.2_FROZEN_PATH","FROZEN_ACTIVE_KB")[0]
        candidate=run_path(C37CFG02,self.candidate,self.candidate_manifest,self.policy,[case],"C37_METADATA_CFG02:metadata_off","C5_REVIEWED_CANDIDATE")[0]
        return {"query":query,"baseline":baseline,"candidate":candidate,"candidate_path_id":"C37_METADATA_CFG02:metadata_off","inference_enabled":False}


service=CandidateRetrievalService()
orchestrator=UnifiedOrchestrator()
app=Flask(__name__)

@app.get("/health")
def health(): return jsonify(service.health())

@app.post("/api/inspect-retrieval")
def inspect_retrieval():
    body=request.get_json(silent=True) or {}; query=(body.get("query") or "").strip()
    if not query: return jsonify({"error":"Query is required."}),400
    return jsonify(service.inspect(query))

@app.post("/api/ask")
def ask():
    body=request.get_json(silent=True) or {}; query=(body.get("query") or "").strip()
    if not query: return jsonify({"error":"Query is required."}),400
    protected={"intent","normalized_intent","route","model","candidate_path_id","evidence_origin","evidence_plan"}
    supplied_protected=sorted(protected & set(body))
    if service.inference is None: service.inference=CandidateInferenceServiceV01()
    prepared=orchestrator.prepare(query,body.get("session_id"),body.get("attachments") or [])
    if body.get("workflow"):
        prepared["workflow"]=body["workflow"]
    if body.get("case_state"):
        prepared["case_state"].update(body["case_state"])
    response=service.inference.infer(prepared,body.get("documents") or [])
    if isinstance(response,dict):
        response["session_id"]=prepared["session_id"]
        orchestrator.remember_assistant(prepared["session_id"],str(response.get("conclusion") or response.get("direct_answer") or ""))
    if supplied_protected:
        meta=dict(response.get("_meta") or {})
        meta["ignored_protected_request_fields"]=supplied_protected
        response["_meta"]=meta
    return jsonify(response)

@app.post("/api/rollback-check")
def rollback_check():
    return jsonify({"status":"AVAILABLE","target":"ACTIVE_KB_V0.2_FROZEN_PATH","candidate_disabled":True,"automatic_reopen_on_failure":True,"live_activation_status":"PROHIBITED_PENDING_PHASE_C_GATES"})
