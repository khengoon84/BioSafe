from pathlib import Path
import sys
HERE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(HERE/"src"))
from phase_c3_2 import artifacts, canonical_bytes, evaluate
kb,manifest,gold=artifacts(); (HERE/"data").mkdir(exist_ok=True); (HERE/"reports").mkdir(exist_ok=True)
for name,value in (("BioSafe_PhaseC3_2_Benchmark_KB_v0_1.json",kb),("BioSafe_PhaseC3_2_Benchmark_Manifest_v0_1.json",manifest),("gold_cases_v0_1.json",gold)):
    (HERE/"data"/name).write_bytes(canonical_bytes(value))
(HERE/"reports/phase_c3_2_retrieval_diagnostics_report_v0_1.json").write_bytes(canonical_bytes(evaluate()))
print(f"C3.2 diagnostics: cases={gold['case_count']} variants=6 result=BLOCKED_PENDING_OWNER_REVIEW")