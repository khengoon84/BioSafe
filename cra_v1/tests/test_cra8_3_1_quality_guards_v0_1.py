import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))

from followup_continuity_guard_v0_1 import is_referential_followup
from integration_quality_guard_v0_1 import enforce_output_domain_and_recommendation_grounding

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

for q in ["why?","Why does that matter?","what about that?","Can you explain this?","what does it mean?"]:
    check(f"referential detected: {q}",is_referential_followup(q))

for q in ["What are the transport requirements?","Review this SOP","Who are you?"]:
    check(f"nonreferential preserved: {q}",not is_referential_followup(q))

review_response={
    "conclusion":"The SOP is missing LMO fields required by Form E.",
    "applicable_authority":["Department of Biosafety / Malaysia"],
    "evidence":[
        {"evidence_id":"CLM-020","statement":"LMO description requires donor/parent organism, vector or method, trait/modified trait."}
    ],
    "missing_information":["Host organism and vector/method details"],
    "recommended_next_step":["Provide missing LMO description fields per Form E requirements."],
    "limitations":[],
    "safety":{"classification":"normal","response_mode":"answer","reason":""},
}
clean,meta=enforce_output_domain_and_recommendation_grounding(
    review_response,
    active_domains=["document_review","general_biosafety"],
    excluded_domains=["form_e","lmo_modern_biotechnology","transport","waste","containment"],
)
text=" ".join([str(clean.get("conclusion",""))]+[str(x) for x in clean.get("recommended_next_step",[])]+[str(x) for x in clean.get("missing_information",[])])
check("review Form E leakage removed","form e" not in text.lower())
check("review LMO leakage removed","lmo" not in text.lower())
check("quality removal recorded",meta["removed_count"]>=1)

forme_response={
    "conclusion":"Form E information is incomplete.",
    "applicable_authority":["Department of Biosafety / Malaysia"],
    "evidence":[
        {"evidence_id":"CLM-020","statement":"LMO description requires donor/parent organism and vector or method."}
    ],
    "missing_information":["Specific donor or parent organism name"],
    "recommended_next_step":[
        "Submit missing donor/organism details to the laboratory director for biosafety clearance.",
        "Provide a detailed description of the modified trait and its function."
    ],
    "limitations":[],
    "safety":{"classification":"normal","response_mode":"answer","reason":""},
}
clean,meta=enforce_output_domain_and_recommendation_grounding(
    forme_response,
    active_domains=["form_e","lmo_modern_biotechnology"],
    excluded_domains=["transport","waste","containment"],
)
steps=" ".join(clean["recommended_next_step"]).lower()
check("unsupported laboratory-director step removed","laboratory director" not in steps)
check("supported substantive next step retained","modified trait" in steps)

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-8.3.1 generalized quality guards: PASS")
