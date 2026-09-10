import sys,json
from pathlib import Path
R=Path("/home/khengoon/biosafe");sys.path.insert(0,str(R/"unified_v1/src"))
from biosafe_unified222 import EvidenceScopeEnforcer
from biosafe_unified221 import EvidenceRequirementPlanner
from biosafe_unified223 import ScopedPipelineAdapter,SemanticClaimVerifier
class P:
 def build_messages(self,q,case_id=None,safety_class=None):
  b={"user_query":q,"route":{},"evidence_bundle":[
   {"evidence_id":"MY","authority":"Department of Biosafety / Malaysia","document_id":"KB-MY-ACT678","text":"notification under Act"},
   {"evidence_id":"WHO","authority":"World Health Organization","document_id":"KB-WHO-LBM4","text":"biosafety risk assessment and containment guidance"}]}
  return b,[{"role":"system","content":"sys"},{"role":"user","content":json.dumps({"user_query":q,"evidence_bundle":b["evidence_bundle"]})}],None
plan=EvidenceRequirementPlanner().plan("educational_answer","What is biosafety?")
a=ScopedPipelineAdapter(P(),EvidenceScopeEnforcer(),plan,"What is biosafety?")
b,m,_=a.build_messages("What is biosafety?");p=json.loads(m[1]["content"]);C=[]
def ck(n,x):C.append((n,bool(x)))
ck("bundle_scoped",[e["evidence_id"] for e in b["evidence_bundle"]]==["WHO"])
ck("message_scoped",[e["evidence_id"] for e in p["evidence_bundle"]]==["WHO"])
ck("audit_removed",a.audit["removed_ids"]==["MY"])
v=SemanticClaimVerifier();r,f=v.apply({"conclusion":"The IBC is a regulatory body. It provides biosafety oversight."},
 [{"text":"The IBC provides biosafety oversight and assesses facilities and practices."}])
ck("unsupported_flagged",len(f)==1);ck("unsupported_removed","regulatory body" not in r["conclusion"].lower())
ck("supported_kept","biosafety oversight" in r["conclusion"].lower())
r2,f2=v.apply({"conclusion":"Prior notification is required."},[{"text":"Prior notification is required for specified activities."}])
ck("supported_reg_claim_kept","prior notification is required" in r2["conclusion"].lower())
for n,x in C:print(f"{n}: {'PASS' if x else 'FAIL'}")
n=sum(x for _,x in C);print(f"Unified-2.2.3 contract: {n}/{len(C)} PASS")
if n!=len(C):raise SystemExit(1)
