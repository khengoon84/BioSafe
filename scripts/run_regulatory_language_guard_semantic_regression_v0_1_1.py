
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV01

cases = json.loads((ROOT/"data"/"regulatory_language_guard_semantic_regression_v0.1.1.json").read_text(encoding="utf-8"))
g = RegulatoryLanguageGuardV01()
results = []
passed = 0

for c in cases:
    fixed, repairs = g.apply(c["input"]["response"], c["input"].get("evidence", []))
    conclusion = fixed["conclusion"]
    exp = c["expect"]
    ok = True
    if exp.get("exact") and conclusion != exp["exact"]:
        ok = False
    if exp.get("contains") and exp["contains"].lower() not in conclusion.lower():
        ok = False
    if exp.get("repair") and exp["repair"] not in repairs:
        ok = False
    if exp.get("repair_absent") and exp["repair_absent"] in repairs:
        ok = False
    results.append({"id":c["id"],"pass":ok,"conclusion":conclusion,"repairs":repairs})
    passed += int(ok)

out = {
    "suite":"BioSafe_Regulatory_Language_Guard_Semantic_Regression_v0.1.1",
    "cases":len(cases),
    "passed":passed,
    "failed":len(cases)-passed,
    "results":results
}
outdir = ROOT/"output"
outdir.mkdir(exist_ok=True)
outfile = outdir/"regulatory_language_guard_semantic_regression_v0.1.1_results.json"
outfile.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"Cases: {len(cases)}")
print(f"PASS: {passed}")
print(f"FAIL: {len(cases)-passed}")
print("Output:", outfile)
if passed != len(cases):
    raise SystemExit(1)
