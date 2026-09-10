import sys
from pathlib import Path
R=Path("/home/khengoon/biosafe");sys.path.insert(0,str(R/"unified_v1/src"))
from biosafe_unified2241 import EvidencePreservingSemanticVerifier
C=[]
def ck(n,x):C.append((n,bool(x)))
v=EvidencePreservingSemanticVerifier()
resp={"conclusion":"PI (Principal Investigator) is responsible for the project. IBC is a regulatory body that reviews and approves biosafety plans."}
ev=[{"evidence_id":"CLM-015","text":"IBC functions include assessment and monitoring of facilities, procedures, practices, training, containment-level assessment and reporting."}]
out,a=v.apply(resp,ev)
ck("pi_preserved","Principal Investigator" in out["conclusion"])
ck("ibc_preserved","Institutional Biosafety Committee" in out["conclusion"])
ck("regulatory_body_removed","regulatory body" not in out["conclusion"].lower())
ck("approval_removed","approves biosafety plans" not in out["conclusion"].lower())
ck("supported_function_present",("assessment" in out["conclusion"].lower() or "monitoring" in out["conclusion"].lower()))
ck("audit_repair",any(x.get("action")=="repair" for x in a))
# Unsupported legal strength without support is removed, not replaced with invented law.
o2,a2=v.apply({"conclusion":"The authority must approve this project."},[{"text":"The guidance describes a review process."}])
ck("unsupported_must_removed","must approve" not in o2["conclusion"].lower())
ck("no_invented_section","section" not in o2["conclusion"].lower())
for n,x in C:print(f"{n}: {'PASS' if x else 'FAIL'}")
p=sum(x for _,x in C);print(f"Unified-2.2.4.1 contract: {p}/{len(C)} PASS")
if p!=len(C):raise SystemExit(1)
