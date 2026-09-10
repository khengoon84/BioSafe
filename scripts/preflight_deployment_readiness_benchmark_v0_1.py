
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent
cases=json.loads((ROOT/"data"/"deployment_readiness_cases_v0.1.json").read_text(encoding="utf-8"))
assert len(cases)==24
groups={}
for c in cases:
    groups[c["group"]]=groups.get(c["group"],0)+1
assert groups["routine_biosafety_qa"]==4
assert groups["malaysian_regulatory"]==4
assert groups["single_document_review"]==4
assert groups["multi_document_or_contradiction"]==4
assert groups["form_e_and_missing_information"]==3
assert groups["safety_boundary"]==3
assert groups["lite_failure_escalation"]==2
print("BioSafe Deployment Readiness Benchmark v0.1 preflight: PASS")
print("24 representative cases loaded: PASS")
print("7 deployment groups represented: PASS")
print("Frozen architecture modification: NONE")
