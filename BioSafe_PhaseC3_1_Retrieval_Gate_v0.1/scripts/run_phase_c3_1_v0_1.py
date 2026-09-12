from pathlib import Path
import sys, json

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
from phase_c3_1 import artifacts, canonical_bytes, evaluate

kb, manifest, gold = artifacts()
(HERE / "data").mkdir(exist_ok=True); (HERE / "reports").mkdir(exist_ok=True)
for name, value in (("BioSafe_PhaseC3_1_Benchmark_KB_v0_1.json", kb), ("BioSafe_PhaseC3_1_Benchmark_Manifest_v0_1.json", manifest), ("gold_cases_v0_1.json", gold)):
    (HERE / "data" / name).write_bytes(canonical_bytes(value))
report = evaluate()
(HERE / "reports/phase_c3_1_retrieval_gate_report_v0_1.json").write_bytes(canonical_bytes(report))
print(f"C3.1 gate benchmark: cases={gold['case_count']} variants=4 result={report['gate_result']}")