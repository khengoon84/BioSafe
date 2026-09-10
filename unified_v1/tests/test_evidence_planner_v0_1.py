
import sys
from pathlib import Path
ROOT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(ROOT/"unified_v1"/"src"))
from biosafe_unified221 import EvidenceRequirementPlanner
p=EvidenceRequirementPlanner(); checks=[]
def ck(n,c):checks.append((n,bool(c)))
x=p.plan("product_help","who are you"); ck("product_no_rag",not x.retrieval_required and x.retrieval_mode=="none")
x=p.plan("simple_answer","hello"); ck("simple_no_rag",not x.retrieval_required)
x=p.plan("follow_up","please elaborate"); ck("followup_context_first",not x.retrieval_required and x.retrieval_mode=="context_only")
x=p.plan("educational_answer","What is biosafety?"); ck("education_general",x.retrieval_required and x.retrieval_mode=="general_guidance")
ck("education_not_regulatory",x.authority_scope=="international_or_foundational")
x=p.plan("educational_answer","Explain the biosafety regulation for this activity"); ck("education_explicit_regulatory",x.retrieval_mode=="regulatory")
x=p.plan("regulatory_assessment","Does Act 678 apply?"); ck("regulatory_required",x.retrieval_required and x.retrieval_mode=="regulatory")
x=p.plan("document_review","Review this SOP",attachments_present=True); ck("document_plus_authority",x.retrieval_mode=="document_plus_authority")
x=p.plan("form_e_assist","Help prepare Form E",attachments_present=True); ck("forme_regulatory",x.retrieval_mode=="form_e_regulatory")
x=p.plan("safety_redirect","unsafe request"); ck("safety_gate_first",not x.retrieval_required)
failed=[n for n,v in checks if not v]
for n,v in checks:print(f"{n}: {'PASS' if v else 'FAIL'}")
print(f"Evidence Planner contract: {len(checks)-len(failed)}/{len(checks)} PASS")
if failed:raise SystemExit(1)
