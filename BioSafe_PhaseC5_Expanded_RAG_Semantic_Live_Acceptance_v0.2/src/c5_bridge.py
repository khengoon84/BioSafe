from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_v0.2/src"),str(ROOT/"BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_v0.2/scripts")]
from retriever_cfg02_base import BioSafeCFG02
from phase_c3_7 import C37CFG02, build_artifacts, canonical_bytes, retrieval_policy

ACTIVE_KB=ROOT/"data/BioSafe_Knowledge_Base_v0.2.json"
ACTIVE_MANIFEST=ROOT/"data/BioSafe_Knowledge_Pack_Manifest_v0.1.json"
HASHES=HERE/"data/frozen_hash_manifest_v0_1.json"
DISPOSITION=HERE/"data/candidate_claim_disposition_v0_1.json"
C37_GOLD=ROOT/"BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_v0.2/data/gold_cases_v0_2.json"

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def enrich(hit: dict[str,Any], claim: dict[str,Any], policy: dict[str,Any], origin: str, path_id: str) -> dict[str,Any]:
    out=dict(hit)
    documents={d["controlled_document_id"]:d for d in policy.get("documents",[])}
    document=documents.get(claim["document_id"],{})
    out.update({"support_spans":claim.get("support_spans",[]),"source_sha256":claim.get("source_sha256") or document.get("source_sha256"),"verification_status":claim.get("verification_status"),"evidence_origin":origin,"candidate_path_id":path_id})
    return out

def validate_hashes() -> list[str]:
    expected=load(HASHES); errors=[]
    for item_name,item in (("active_kb",expected["active_kb"]),("active_manifest",expected["active_manifest"])):
        if digest(ROOT/item["path"])!=item["sha256"]: errors.append(f"{item_name}_hash_mismatch")
    for path,value in expected["frozen_components"].items():
        if digest(ROOT/path)!=value: errors.append(f"frozen_hash_mismatch:{path}")
    return errors

def run_path(cls, kb: dict[str,Any], manifest: dict[str,Any], policy: dict[str,Any], cases: list[dict[str,Any]], path_id: str, origin: str) -> list[dict[str,Any]]:
    claims={c["claim_id"]:c for c in kb["claims"]}
    with tempfile.TemporaryDirectory() as td:
        p=Path(td); kp=p/"kb.json"; mp=p/"manifest.json"; pp=p/"policy.json"
        kp.write_bytes(canonical_bytes(kb));mp.write_bytes(canonical_bytes(manifest));pp.write_bytes(canonical_bytes(policy))
        retriever=cls(kp,mp,policy_path=pp,metadata_layer=False) if cls is C37CFG02 else cls(kp,mp)
        results=[]
        for case in cases:
            profile,hits=retriever.retrieve(case["query"],top_k=10); enriched=[enrich(h,claims[h["claim_id"]],policy,origin,path_id) for h in hits if h["claim_id"] in claims]
            ids=[h["claim_id"] for h in enriched]; acceptable=set(case.get("acceptable_claim_ids",[])); ranks=[ids.index(x)+1 for x in acceptable if x in ids]
            results.append({"case_id":case["case_id"],"path_id":path_id,"query":case["query"],"route":profile.__dict__,"ranked_claim_ids":ids,"ranked_document_ids":[h["document_id"] for h in enriched],"first_acceptable_rank":min(ranks) if ranks else None,"retrieval_ok":bool(ranks) if acceptable else not enriched,"evidence":[{k:h.get(k) for k in ("claim_id","document_id","support_spans","source_sha256","verification_status","evidence_origin","candidate_path_id")} for h in enriched]})
        return results

def evaluate() -> dict[str,Any]:
    errors=validate_hashes(); active=load(ACTIVE_KB); manifest=load(ACTIVE_MANIFEST); candidate,candidate_manifest,_=build_artifacts(); policy=retrieval_policy(); disposition=load(DISPOSITION)
    active_ids={c["claim_id"] for c in active["claims"]}; candidate_ids={c["claim_id"] for c in candidate["claims"]}
    if active_ids & candidate_ids != candidate_ids: errors.append("candidate_claim_identity_mismatch")
    if sorted(disposition["active_only_claim_ids"]) != sorted(active_ids-candidate_ids): errors.append("active_only_disposition_mismatch")
    if errors: return {"artifact_version":"BioSafe_Phase5_C5_Preflight_Report_v0.1","result":"C3_REOPENED_BY_TRIGGER","errors":errors}
    gold=[c for c in load(C37_GOLD)["cases"] if c["case_type"] not in {"unknown_evidence","currentness","conflict"} and not c["case_id"].startswith("C37-F-")]
    baseline=run_path(BioSafeCFG02,active,manifest,policy,gold,"ACTIVE_KB_V0.2_FROZEN_PATH","FROZEN_ACTIVE_KB")
    reviewed=run_path(C37CFG02,candidate,candidate_manifest,policy,gold,"C37_METADATA_CFG02:metadata_off","C5_REVIEWED_CANDIDATE")
    return {"artifact_version":"BioSafe_Phase5_C5_Preflight_Report_v0.1","result":"READY_FOR_C5_DETERMINISTIC_SEMANTIC_STAGE","candidate":"C37_METADATA_CFG02:metadata_off","control_path":"ACTIVE_KB_V0.2_FROZEN_PATH","active_kb_sha256":digest(ACTIVE_KB),"active_manifest_sha256":digest(ACTIVE_MANIFEST),"claim_disposition":disposition,"case_count":len(gold),"baseline":baseline,"candidate_results":reviewed,"candidate_evidence_origin":"C5_REVIEWED_CANDIDATE","synthetic_fixture_excluded":True,"rollback":{"status":"AVAILABLE","target":"ACTIVE_KB_V0.2_FROZEN_PATH","automatic_reopen_on_failure":True},"claim_use_status":"REVIEW_REQUIRED_BEFORE_CLAIM_USE","live_activation_status":"PROHIBITED_PENDING_PHASE_C_GATES","live_status":"BLOCKED_UNTIL_C5_CANDIDATE_SERVICE_AND_ENVIRONMENT_PREFLIGHT"}