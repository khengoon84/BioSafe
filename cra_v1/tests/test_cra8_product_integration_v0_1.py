import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))
from cra_contracts_v0_1 import *
from cra_product_integration_v0_1 import integrate_turn

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

# Product help bypasses regulatory pipeline
c=ConversationState(session_id="s"); case=CaseState(case_id="c")
r=integrate_turn("who are you?","t1",c,case)
check("identity bypass route",r.route=="product_help_bypass")
check("identity skips RAG",r.evidence_plan.skip_rag)
check("identity renders product help",r.rendered_response["response_type"]=="product_help")
check("identity no evidence sections",r.rendered_response["sections"]==[])

# Document capability bypass
c=ConversationState(session_id="s2"); case=CaseState(case_id="c2")
r=integrate_turn("what kind of document can you review?","t1",c,case)
check("document help bypass",r.route=="product_help_bypass")
check("document help no domains",r.task_frame.activated_domains==[])
check("document help useful answer","SOP" in r.rendered_response["direct_answer"])

# Form E product help must not invoke Form E regulatory workflow
c=ConversationState(session_id="s3"); case=CaseState(case_id="c3")
r=integrate_turn("how does the Form E Assistant work?","t1",c,case)
check("Form E help bypass",r.route=="product_help_bypass")
check("Form E help no Form E domain","form_e" not in r.task_frame.activated_domains)
check("Form E help boundary stated","does not simulate IBC approval" in r.rendered_response["direct_answer"])

# Generic domain question reaches adapter, but only general biosafety
c=ConversationState(session_id="s4")
case=CaseState(case_id="c4",jurisdiction=FactValue(value="Malaysia",status=FactStatus.USER_CONFIRMED,source="user",confidence=1))
r=integrate_turn("What is the biosafety requirement for this work?","t1",c,case)
check("domain route pending adapter",r.route=="domain_adapter_pending")
check("generic biosafety only",r.task_frame.activated_domains==["general_biosafety"])
check("generic excludes Form E","form_e" in r.evidence_plan.exclude_domains)
check("generic excludes transport","transport" in r.evidence_plan.exclude_domains)
check("generic excludes waste","waste" in r.evidence_plan.exclude_domains)

# Explicit transport reaches constrained adapter
c=ConversationState(session_id="s5"); case=CaseState(case_id="c5")
r=integrate_turn("What are the transport requirements for this specimen?","t1",c,case)
check("transport adapter pending",r.route=="domain_adapter_pending")
check("transport constrained",r.retrieval_request["required_domains"]==["transport"])
check("transport excludes Form E","form_e" in r.retrieval_request["exclude_domains"])

# Callback proves adapter handoff works without changing frozen core
def fake_domain(frame,plan,retrieval):
    return {"response_type":"test","domains":retrieval["required_domains"]}
r=integrate_turn("What are the transport requirements for this specimen?","t2",ConversationState(session_id="s6"),CaseState(case_id="c6"),fake_domain)
check("domain callback route",r.route=="domain_adapter")
check("domain callback receives constraint",r.rendered_response["domains"]==["transport"])

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-8 Product Integration Scaffold v0.1: PASS")
