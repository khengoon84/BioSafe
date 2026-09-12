from pathlib import Path
import sys
HERE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(HERE/"src")); sys.path.insert(0,str(HERE/"scripts"))
from phase_c3_6 import artifacts, canonical_bytes, evaluate
from build_retrieval_policy import build_artifact
(HERE/"data").mkdir(exist_ok=True); (HERE/"reports").mkdir(exist_ok=True)
policy,gold=artifacts(); (HERE/"data/retrieval_policy_v0_1.json").write_bytes(canonical_bytes(policy)); (HERE/"data/gold_cases_v0_1.json").write_bytes(canonical_bytes(gold)); (HERE/"reports/phase_c3_6_retrieval_correction_report_v0_1.json").write_bytes(canonical_bytes(evaluate()))
print("C3.6 retrieval correction: result=BLOCKED_PENDING_OWNER_REVIEW")