import sys
from pathlib import Path
R=Path("/home/khengoon/biosafe");sys.path.insert(0,str(R/"unified_v1/src"))
from biosafe_unified2242 import SubjectAwareEvidenceScopeEnforcer
C=[]
def ck(n,x):C.append((n,bool(x)))
class R:
 def __init__(self,evidence,removed,mode):
  self.evidence=evidence;self.removed=removed;self.mode=mode
class Base:
 def apply(self,evidence,plan,query):
  keep=[e for e in evidence if e["evidence_id"]=="WHO"]
  rem=[e for e in evidence if e["evidence_id"]!="WHO"]
  return R(keep,rem,"general_guidance")
e=[
 {"evidence_id":"WHO","title":"WHO biosafety","text":"general biosafety risk assessment","document_id":"KB-WHO-LBM4"},
 {"evidence_id":"IBC_ROLE","title":"IBC guideline","text":"IBC functions include assessment and monitoring of facilities, procedures and practices; institutional biosafety oversight.","document_id":"KB-MY-IBC"},
 {"evidence_id":"FORME","title":"Form E","text":"The IBC Assessment Report is completed by the registered IBC.","document_id":"KB-MY-FORME"},
 {"evidence_id":"ACT","title":"Biosafety Act","text":"The Act regulates specified LMO activities.","document_id":"KB-MY-ACT678"}]
s=SubjectAwareEvidenceScopeEnforcer();s.base=Base()
r=s.apply(e,{"mode":"general_guidance"},"What is PI and IBC?")
ids=[x["evidence_id"] for x in r.evidence]
ck("who_kept","WHO" in ids)
ck("ibc_role_restored","IBC_ROLE" in ids)
ck("forme_not_restored","FORME" not in ids)
ck("act_not_restored","ACT" not in ids)
r2=s.apply(e,{"mode":"general_guidance"},"What is biosafety?")
ids2=[x["evidence_id"] for x in r2.evidence]
ck("plain_definition_no_my_restore",ids2==["WHO"])
for n,x in C:print(f"{n}: {'PASS' if x else 'FAIL'}")
p=sum(x for _,x in C);print(f"Unified-2.2.4.2 contract: {p}/{len(C)} PASS")
if p!=len(C):raise SystemExit(1)
