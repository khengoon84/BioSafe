from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from contracts import BenchmarkCase
from phase_c3_7 import ACTIVATION, BOUNDARIES, C37CFG02, CONFIG, FIXTURES, STATUS, _fixture, _run, build_artifacts, canonical_bytes, retrieval_policy, validate_cases
from metrics import summarize

HERE=Path(__file__).resolve().parents[1]
CASES=HERE/"data/provisional_stress_cases_v0_1.json"
DECISION=HERE/"data/provisional_owner_review_decision_v0_1.json"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases(kb: dict[str, Any]) -> tuple[dict[str, Any],list[BenchmarkCase]]:
    artifact=json.loads(CASES.read_text(encoding="utf-8")); claims={c["claim_id"]:c for c in kb["claims"]}; rows=[]
    for source in artifact["cases"]:
        row=dict(source); ids=row.get("acceptable_claim_ids",[])
        row["acceptable_document_ids"]=sorted({claims[cid]["document_id"] for cid in ids})
        if len(ids)==1 and "support_span" in row.get("metrics",[]):
            row["expected_source_record_ids"]=sorted({s["source_record_id"] for s in claims[ids[0]]["support_spans"]})
        else:
            row["expected_source_record_ids"]=[]
        row["partition"]="provisional_non_independent"
        rows.append(BenchmarkCase.from_dict(row))
    return artifact,rows


def evaluate() -> dict[str, Any]:
    kb,manifest,_=build_artifacts(); policy=retrieval_policy(); fkb,fpol,fixture=_fixture(kb,policy)
    artifact,cases=load_cases(kb); errors=validate_cases(cases,fkb,fpol)
    common={"artifact_version":"BioSafe_PhaseC3_7_Provisional_Stress_Report_v0.1","benchmark_mode":"PROVISIONAL_NON_INDEPENDENT_NOT_A_C3_CLOSURE_GATE","authorship_status":artifact["authorship_status"],"candidate":artifact["candidate_locked_before_execution"],"input_hashes":{"stress_cases":_hash(CASES),"query_profile_config":_hash(CONFIG),"boundary_contracts":_hash(BOUNDARIES)},"artifact_validation_errors":errors,"claim_use_status":STATUS,"live_activation_status":ACTIVATION,"gate_result":"BLOCKED_INDEPENDENT_HOLDOUT_AND_OWNER_REVIEW"}
    if errors:
        return {**common,"provisional_result":"INVALID_BENCHMARK_ARTIFACT","summary":{},"cases":[]}
    results=_run(C37CFG02,fkb,manifest,fpol,cases,False); summary=summarize(results)
    passed=all(summary["hard_gates"].values())
    return {**common,"provisional_result":"PROVISIONAL_PASS_NOT_GATE_ELIGIBLE" if passed else "PROVISIONAL_FAIL_NOT_GATE_ELIGIBLE","summary":summary,"cases":[r.as_dict() for r in results]}


def owner_review_packet(report: dict[str, Any]) -> dict[str, Any]:
    kb,_,_=build_artifacts(); claims={c["claim_id"]:c for c in kb["claims"]}
    artifact=json.loads(CASES.read_text(encoding="utf-8")); source_cases={c["case_id"]:c for c in artifact["cases"]}
    boundary_contracts=json.loads(BOUNDARIES.read_text(encoding="utf-8"))["contracts"]
    rows=[]
    for result in report["cases"]:
        source=source_cases[result["case_id"]]; acceptable=[cid for cid in result["ranked_claim_ids"] if cid in source.get("acceptable_claim_ids",[])]
        evidence=[{"claim_id":cid,"document_id":claims[cid]["document_id"],"text":claims[cid]["text"],"support_spans":claims[cid]["support_spans"]} for cid in acceptable]
        expected={"query":source["query"],"case_type":source["case_type"],"acceptable_claim_ids":source.get("acceptable_claim_ids",[]),"expected_jurisdiction":source["expected_jurisdiction"],"retrieval_must_be_empty":source.get("retrieval_must_be_empty",False),"required_boundary":source.get("required_boundary"),"boundary_contract_documents":boundary_contracts.get(source.get("required_boundary"),[])}
        rows.append({"case_id":result["case_id"],"review_status":"OWNER_REVIEW_REQUIRED","owner_disposition":None,"findings":None,"expected_contract":expected,"retrieved_acceptable_evidence":evidence,"checks":{"query_contract_is_valid":None,"route_is_semantically_correct":None,"retrieved_claim_is_responsive":None,"boundary_is_preserved":None,"provenance_is_adequate":None,"uncertainty_is_preserved":None},"observed_result":result})
    decision=json.loads(DECISION.read_text(encoding="utf-8")) if DECISION.exists() else {}
    return {"artifact_version":"BioSafe_PhaseC3_7_Provisional_Owner_Review_Packet_v0.1","review_scope":"PROVISIONAL_STRESS_RESULTS_NOT_C3_APPROVAL","stress_report_sha256":hashlib.sha256(canonical_bytes(report)).hexdigest(),"owner_decision_sha256":_hash(DECISION) if DECISION.exists() else None,"reviewer_identity":decision.get("reviewer_identity"),"reviewer_role":decision.get("reviewer_role"),"review_date":decision.get("review_date"),"permitted_dispositions":["ACCEPT_PROVISIONAL_RESULT","CORRECTION_REQUIRED","REJECT_CASE_CONTRACT","UNRESOLVED"],"overall_disposition":decision.get("overall_disposition"),"overall_finding":decision.get("finding"),"scope_acknowledgements":decision.get("scope_acknowledgements",{}),"granular_case_attestations":"NOT_PROVIDED_REMAIN_UNSET","claim_use_status":STATUS,"live_activation_status":ACTIVATION,"cases":rows}