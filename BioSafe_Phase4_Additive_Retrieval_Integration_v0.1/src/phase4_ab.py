from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_v0.2/src"),str(ROOT/"BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_v0.2/scripts")]
from phase_c3_7 import C37CFG02, canonical_bytes, retrieval_policy

ACTIVE_KB=ROOT/"data/BioSafe_Knowledge_Base_v0.2.json"
ACTIVE_MANIFEST=ROOT/"data/BioSafe_Knowledge_Pack_Manifest_v0.1.json"
CANDIDATE_GOLD=ROOT/"BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_v0.2/data/gold_cases_v0_2.json"
EXPECTED={"kb":"3d68f8154f6952a33395b253925ee44c2842a046c3c11d55f8c12ee9eb386bb4","manifest":"199145afd64b1fb41f38921aba90ac214193f199dda4eb29f649c10eadf11031"}

def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def evaluate() -> dict[str, Any]:
    errors=[]
    for name,path in (("kb",ACTIVE_KB),("manifest",ACTIVE_MANIFEST)):
        if digest(path)!=EXPECTED[name]: errors.append(f"{name}_hash_mismatch")
    gold=json.loads(CANDIDATE_GOLD.read_text())
    candidate_ids={c["case_id"] for c in gold["cases"]}
    if any(c.startswith("C37-F-") for c in candidate_ids): errors.append("synthetic_fixture_in_candidate_corpus")
    if errors: return {"artifact_version":"BioSafe_Phase4_Additive_Retrieval_Integration_Report_v0.1","result":"C3_REOPENED_BY_TRIGGER","errors":errors}
    # This package proves wiring and rollback identity only; semantic/live acceptance belongs to C5.
    return {"artifact_version":"BioSafe_Phase4_Additive_Retrieval_Integration_Report_v0.1","result":"READY_FOR_C5_SEMANTIC_LIVE_ACCEPTANCE","candidate":"C37_METADATA_CFG02:metadata_off","control_path":"ACTIVE_KB_V0.2_FROZEN_PATH","active_kb_sha256":digest(ACTIVE_KB),"active_manifest_sha256":digest(ACTIVE_MANIFEST),"candidate_case_count":len(candidate_ids),"synthetic_fixture_excluded":True,"live_activation_status":"PROHIBITED_PENDING_PHASE_C_GATES","claim_use_status":"REVIEW_REQUIRED_BEFORE_CLAIM_USE","rollback":{"status":"AVAILABLE","path":"ACTIVE_KB_V0.2_FROZEN_PATH","automatic_reopen_on_failure":True},"limitations":["Deterministic wiring/A-B readiness only; C5 semantic and live WSL2/Ollama acceptance is required.","No independent holdout was completed."]}