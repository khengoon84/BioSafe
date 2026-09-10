import sys
from pathlib import Path
R=Path("/home/khengoon/biosafe");sys.path.insert(0,str(R/"unified_v1/src"))
from biosafe_unified224 import ResponseTypeContractEnforcer,SemanticRepairLayer
C=[]
def ck(n,x):C.append((n,bool(x)))
sample={"conclusion":"Biosafety is...","missing_information":["Current Malaysian regulations"],
"recommended_next_step":["Identify Malaysian framework"],
"limitations":["Document review is advisory and does not certify regulatory compliance or approval."],
"safety":{"classification":"caution","response_mode":"answer","reason":"Document review is advisory."}}
o,a=ResponseTypeContractEnforcer().apply(sample,"educational_answer")
ck("edu_missing_cleared",o["missing_information"]==[])
ck("edu_next_cleared",o["recommended_next_step"]==[])
ck("edu_boilerplate_removed",o["limitations"]==[])
ck("edu_safety_normalized",o["safety"]["classification"]=="normal")
reg=ResponseTypeContractEnforcer().apply(sample,"regulatory_assessment")[0]
ck("reg_missing_preserved",len(reg["missing_information"])==1)
ck("reg_next_preserved",len(reg["recommended_next_step"])==1)
r=SemanticRepairLayer()
fixed,audit=r.repair({"conclusion":"PI means Principal Investigator."},
 [{"sentence":"IBC is a regulatory body.","unsupported_predicates":["regulatory body"]}],
 [{"statement":"IBC functions include assessment and monitoring of facilities, procedures, practices and containment."}],
 "What is PI and IBC?")
ck("repair_ibc_present","IBC means Institutional Biosafety Committee" in fixed["conclusion"])
ck("repair_no_regulatory_body","regulatory body" not in fixed["conclusion"].lower())
ck("repair_audited",len(audit)==1)
for n,x in C:print(f"{n}: {'PASS' if x else 'FAIL'}")
p=sum(x for _,x in C);print(f"Unified-2.2.4 contract: {p}/{len(C)} PASS")
if p!=len(C):raise SystemExit(1)
