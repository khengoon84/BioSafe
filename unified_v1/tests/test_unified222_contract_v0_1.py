
import sys
from pathlib import Path
R=Path("/home/khengoon/biosafe");sys.path.insert(0,str(R/"unified_v1/src"))
from biosafe_unified222 import canonicalize,normalize_intent,EvidenceScopeEnforcer
checks=[]
def ck(n,c):checks.append((n,bool(c)))
ck("canonical_u",canonicalize("Do U know who I am?")=="do you know who i am")
ck("self_knowledge",normalize_intent("do u know who i am?","simple_answer")=="self_knowledge")
ck("self_knowledge_caps",normalize_intent("DO YOU KNOW ME?!","follow_up")=="self_knowledge")
ck("identity",normalize_intent("Who are you?","follow_up")=="product_help")
e=[
 {"evidence_id":"MY1","document_id":"KB-MY-ACT678","authority":"Department of Biosafety / Malaysia","text":"notification under the Act"},
 {"evidence_id":"WHO1","document_id":"KB-WHO-LBM4","authority":"World Health Organization","text":"laboratory biosafety risk-based guidance"},
 {"evidence_id":"FORM","document_id":"KB-MY-FORME","authority":"Department of Biosafety / Malaysia","text":"Form E IBC Assessment Report"},
]
s=EvidenceScopeEnforcer()
r=s.apply(e,{"retrieval_mode":"general_guidance"},"What is biosafety?")
ck("general_keeps_who",[x["evidence_id"] for x in r.evidence]==["WHO1"])
ck("general_removes_my",set(x["evidence_id"] for x in r.removed)=={"MY1","FORM"})
r=s.apply(e,{"retrieval_mode":"regulatory"},"Does Act 678 apply?")
ck("regulatory_preserves",len(r.evidence)==3)
r=s.apply(e,{"retrieval_mode":"none"},"who are you")
ck("none_removes_all",len(r.evidence)==0)
for n,v in checks:print(f"{n}: {'PASS' if v else 'FAIL'}")
p=sum(v for _,v in checks);print(f"Unified-2.2.2 contract: {p}/{len(checks)} PASS")
if p!=len(checks):raise SystemExit(1)
