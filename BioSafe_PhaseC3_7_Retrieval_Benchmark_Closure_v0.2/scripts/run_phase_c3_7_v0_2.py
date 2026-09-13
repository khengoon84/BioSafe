from pathlib import Path
import sys
HERE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(HERE/"src")); sys.path.insert(0,str(HERE/"scripts"))
from phase_c3_7 import artifacts, canonical_bytes, evaluate
(HERE/"data").mkdir(exist_ok=True); (HERE/"reports").mkdir(exist_ok=True)
policy,gold=artifacts(); (HERE/"data/retrieval_policy_v0_2.json").write_bytes(canonical_bytes(policy)); (HERE/"data/gold_cases_v0_2.json").write_bytes(canonical_bytes(gold)); report=evaluate(); (HERE/"reports/phase_c3_7_retrieval_benchmark_closure_report_v0_2.json").write_bytes(canonical_bytes(report))
print(f"C3.7 retrieval benchmark integrity correction: result={report['machine_gate_result']}")