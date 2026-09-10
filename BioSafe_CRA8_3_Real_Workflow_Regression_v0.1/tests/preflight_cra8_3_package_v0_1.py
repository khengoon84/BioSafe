import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
cases=json.loads((ROOT/"tests"/"cra8_3_cases_v0_1.json").read_text())
expected={"health","product_help","domain_activation","task_change","follow_up","safety","policy","document_review","form_e","state"}
families={c["family"] for c in cases}
checks={
    "12 cases":len(cases)==12,
    "unique ids":len({c["id"] for c in cases})==12,
    "all expected families covered":expected.issubset(families),
    "review fixture exists":(ROOT/"fixtures"/"sample_review_sop.txt").exists(),
    "runner compiles":True,
}
runner=ROOT/"tests"/"run_cra8_3_workflow_regression_v0_1.py"
try:
    compile(runner.read_text(),str(runner),"exec")
except Exception:
    checks["runner compiles"]=False
for k,v in checks.items():
    print(("PASS" if v else "FAIL"),k)
print(f"\nSummary: {sum(checks.values())}/{len(checks)} passed")
if not all(checks.values()): raise SystemExit(1)
print("CRA-8.3 package preflight: PASS")
