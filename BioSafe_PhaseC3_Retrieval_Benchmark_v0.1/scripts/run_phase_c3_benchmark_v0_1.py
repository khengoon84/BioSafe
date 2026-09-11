from __future__ import annotations
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "src"))
from phase_c3_benchmark import build_artifacts, canonical_bytes, evaluate

kb, manifest, gold = build_artifacts()
(HERE / "data").mkdir(exist_ok=True)
(HERE / "reports").mkdir(exist_ok=True)
(HERE / "data/BioSafe_PhaseC3_Benchmark_KB_v0_1.json").write_bytes(canonical_bytes(kb))
(HERE / "data/BioSafe_PhaseC3_Benchmark_Manifest_v0_1.json").write_bytes(canonical_bytes(manifest))
(HERE / "data/gold_cases_v0_1.json").write_bytes(canonical_bytes(gold))
report = evaluate(kb, manifest, gold)
(HERE / "reports/phase_c3_retrieval_benchmark_v0_1.json").write_bytes(canonical_bytes(report))
print(f"C3 descriptive benchmark: cases={report['case_count']} CFG-01/CFG-02 evaluated; no hard gate")