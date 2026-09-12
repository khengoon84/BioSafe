from pathlib import Path
import sys
HERE=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(HERE/"src"))
from phase_c3_3 import artifacts,canonical_bytes,evaluate
kb,m,g=artifacts(); (HERE/"data").mkdir(exist_ok=True); (HERE/"reports").mkdir(exist_ok=True)
for n,v in (("BioSafe_PhaseC3_3_Benchmark_KB_v0_1.json",kb),("BioSafe_PhaseC3_3_Benchmark_Manifest_v0_1.json",m),("gold_cases_v0_1.json",g)): (HERE/"data"/n).write_bytes(canonical_bytes(v))
(HERE/"reports/phase_c3_3_retrieval_oracle_report_v0_1.json").write_bytes(canonical_bytes(evaluate()))
print(f"C3.3 oracle diagnostics: cases={g['case_count']} variants=6 result=BLOCKED_PENDING_OWNER_REVIEW")