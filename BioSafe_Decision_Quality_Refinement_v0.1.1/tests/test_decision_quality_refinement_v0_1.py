
import sys
from pathlib import Path

PKG=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(PKG/"src"))
from decision_quality_refinement_v0_1 import BioSafeDecisionQualityRefinementV01

g=BioSafeDecisionQualityRefinementV01()

def base():
    return {
        "_meta": {
            "regulatory_applicability_guard": {
                "changed": True,
                "rule_ids": ["RAGUARD-MY-LMO-001"],
                "trigger_status": "unknown"
            }
        },
        "conclusion": "The information supplied is insufficient to determine whether notification is required.",
        "missing_information": [
            "Whether the organism or activity involves a living modified organism (LMO), genetic modification, recombinant technology, or another form of modern biotechnology",
            "Specific hazard classification of Bacillus antracts",
            "Current facility class and transport category"
        ],
        "recommended_next_step": [
            "Clarify whether the organism or activity is genetically modified."
        ],
        "limitations": [],
        "safety": {"classification":"caution","response_mode":"ask_before_concluding","reason":""}
    }

cases=[]

r=g.apply(base(), user_query="I am working with Bacillus antracts. Do I need to notify the Director General?")
mi=" | ".join(r.response["missing_information"]).lower()
recs=" | ".join(r.response["recommended_next_step"]).lower()
cases.append(("DQ-001-remove-ungrounded-transport", "transport category" not in mi))
cases.append(("DQ-002-keep-lmo-trigger", "living modified organism" in mi))
cases.append(("DQ-003-flag-entity-uncertainty", "confirm the organism name" in mi))
cases.append(("DQ-004-actionable-next-step", "please provide or confirm" in recs))
cases.append(("DQ-005-explain-why", "trigger facts" in recs))

r2=g.apply(
    {
        "conclusion":"The information supplied is insufficient to determine transport classification.",
        "missing_information":["Current transport category"],
        "recommended_next_step":[],
        "limitations":[],
        "safety":{}
    },
    user_query="We need to ship this infectious substance by courier."
)
cases.append(("DQ-006-transport-kept-when-grounded", any("transport" in x.lower() for x in r2.response["missing_information"])))

r3=g.apply(
    {
        "conclusion":"A biosafety risk assessment is used to evaluate risk.",
        "missing_information":[],
        "recommended_next_step":[],
        "limitations":[],
        "safety":{}
    },
    user_query="What is the purpose of a biosafety risk assessment?"
)
cases.append(("DQ-007-generic-answer-unchanged", not r3.changed))

failed=[cid for cid,ok in cases if not ok]
for cid,ok in cases:
    print(("PASS" if ok else "FAIL"),cid)
print(f"\nSummary: {len(cases)-len(failed)}/{len(cases)} passed")
if failed:
    raise SystemExit("Failures: "+", ".join(failed))
print("Decision Quality Refinement v0.1 regression: PASS")
