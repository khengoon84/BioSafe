import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from biosafe_unified2.core import UnifiedOrchestrator,strip_internal_metadata,dedupe_user_sections
o=UnifiedOrchestrator(); checks=[]
def ck(n,c): checks.append((n,bool(c)))
p=o.prepare("who are you"); ck("identity product-help",p["intent"]=="product_help"); sid=p["session_id"]
p=o.prepare("do u know who i am?",sid); ck("self-knowledge product-help",p["intent"]=="product_help")
p=o.prepare("What is the difference of biosafety and biosecurity?",sid); ck("educational routing",p["intent"]=="educational_answer")
p=o.prepare("Please elaborate",sid); ck("genuine elaboration follow-up",p["intent"]=="follow_up")
p=o.prepare("what is PI, IBC",sid); ck("acronym self-contained",p["intent"]=="educational_answer")
p=o.prepare("Does Act 678 apply to my project?",sid); ck("regulatory routing",p["intent"]=="regulatory_assessment"); ck("no inferred LMO","genetic_modification_mentioned" not in p["case_state"]); ck("elicits trigger",any(x["field"]=="modern_biotechnology_trigger" for x in p["missing_information"]))
p2=o.prepare("My project uses recombinant E. coli in Malaysia.",sid); ck("jurisdiction case state",p2["case_state"].get("jurisdiction")=="Malaysia"); ck("GM mention case state",p2["case_state"].get("genetic_modification_mentioned") is True)
p3=o.prepare("Use this proposal to help me prepare Form E.",attachments=[{"name":"proposal.pdf"}]); ck("attachment form-e",p3["intent"]=="form_e_assist" and p3["workflow"]=="form-e")
p4=o.prepare("Review this SOP for biosafety gaps.",attachments=[{"name":"sop.pdf"}]); ck("attachment review",p4["intent"]=="document_review" and p4["workflow"]=="review")
dirty={"route":"x","task_frame":{"x":1},"answer":"ok","nested":{"_meta":{"x":1},"safe":"yes"}}; clean=strip_internal_metadata(dirty); ck("metadata strip","route" not in clean and "task_frame" not in clean and "_meta" not in clean["nested"])
d=dedupe_user_sections({"information_needed":["a"],"recommended_next_steps":["b"],"evidence":["c"],"why_this_matters":["c"]}); ck("missing dedupe",d.get("what_i_need_from_you")==["a"] and "information_needed" not in d); ck("next dedupe",d.get("next_step")==["b"] and "recommended_next_steps" not in d); ck("evidence dedupe","why_this_matters" not in d)
failed=[n for n,v in checks if not v]
for n,v in checks: print(f"{n}: {'PASS' if v else 'FAIL'}")
print(f"Unified-2 deterministic contract: {len(checks)-len(failed)}/{len(checks)} PASS")
if failed: raise SystemExit(1)
