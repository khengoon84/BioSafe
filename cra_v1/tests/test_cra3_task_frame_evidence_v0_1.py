import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))

from cra_contracts_v0_1 import *
from interaction_manager_v0_1 import classify_interaction
from task_frame_builder_v0_1 import build_task_frame
from evidence_requirement_planner_v0_1 import plan_evidence
from retrieval_request_adapter_v0_1 import build_retrieval_request

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

def case_my():
    return CaseState(
        case_id="c",
        jurisdiction=FactValue(value="Malaysia",status=FactStatus.USER_CONFIRMED,source="user",confidence=1.0)
    )

# 1 product help
c=case_my()
i=classify_interaction("what kind of document can you review?",ConversationState(session_id="s"))
f=build_task_frame("what kind of document can you review?",i,c)
p=plan_evidence(f)
check("product help activates no domain",f.activated_domains==[])
check("product help skips RAG",p.skip_rag)

# 2 generic biosafety should not activate Form E/transport/waste
i=classify_interaction("What is the biosafety requirement for this work?",ConversationState(session_id="s"))
f=build_task_frame("What is the biosafety requirement for this work?",i,c)
check("generic biosafety active","general_biosafety" in f.activated_domains)
check("generic biosafety excludes Form E","form_e" in f.inactive_domains)
check("generic biosafety excludes transport","transport" in f.inactive_domains)
check("generic biosafety excludes waste","waste" in f.inactive_domains)

# 3 explicit transport
i=classify_interaction("What are the transport requirements for this specimen?",ConversationState(session_id="s"))
f=build_task_frame("What are the transport requirements for this specimen?",i,c)
p=plan_evidence(f)
check("transport explicitly activated","transport" in f.activated_domains)
check("transport evidence planned","transport" in p.required_domains)
check("Form E excluded from transport","form_e" in p.exclude_domains)

# 4 explicit Form E
i=classify_interaction("Do I need Form E for this activity?",ConversationState(session_id="s"))
f=build_task_frame("Do I need Form E for this activity?",i,c)
p=plan_evidence(f)
check("Form E explicitly activated","form_e" in f.activated_domains)
check("Form E evidence planned","form_e" in p.required_domains)

# 5 species alone must not activate LMO
i=classify_interaction("I am working with Bacillus anthracis. What is the biosafety requirement?",ConversationState(session_id="s"))
f=build_task_frame("I am working with Bacillus anthracis. What is the biosafety requirement?",i,c)
check("species mention does not activate LMO","lmo_modern_biotechnology" not in f.activated_domains)
check("species mention does not activate Form E","form_e" not in f.activated_domains)

# 6 follow-up inherits active domain only
c2=case_my(); c2.active_domains=["general_biosafety"]
i=InteractionResult(InteractionType.FOLLOW_UP,0.95,referential_target="concept.notification",candidate_task="explain_or_resolve_previous_concept",needs_domain_pipeline=True)
f=build_task_frame("what approval did you mean?",i,c2,resolved_reference="concept.notification")
check("follow-up inherits current domain",f.activated_domains==["general_biosafety"])
check("follow-up does not activate Form E","form_e" not in f.activated_domains)
check("follow-up decision is explain concept",f.decisions_requested==["explain_previous_concept"])

# 7 follow-up with no active domain skips RAG rather than inventing one
c3=case_my()
f=build_task_frame("why?",i,c3,resolved_reference="concept.notification")
p=plan_evidence(f)
check("context-only follow-up skips RAG",p.skip_rag)

# 8 task change activates only requested domain
i=InteractionResult(InteractionType.TASK_CHANGE,0.95,candidate_task="change_active_task",needs_domain_pipeline=True)
f=build_task_frame("Actually, I only want to know about transport.",i,c2)
check("task change activates transport",f.activated_domains==["transport"])
check("task change deactivates general domain","general_biosafety" not in f.activated_domains)

# 9 evidence adapter
p=plan_evidence(f)
r=build_retrieval_request(f,p)
check("retrieval request not skipped",r["skip"] is False)
check("retrieval request constrained to transport",r["required_domains"]==["transport"])
check("retrieval query domain-focused","transport" in r["query"].lower())

# 10 case unknowns propagate to task frame
c4=case_my(); c4.open_questions=["activity_type","lmo_status"]
i=classify_interaction("Do I need Form E?",ConversationState(session_id="s"))
f=build_task_frame("Do I need Form E?",i,c4)
check("case unknowns copied to frame",set(f.relevant_unknowns)=={"activity_type","lmo_status"})

# 11 waste doesn't activate transport
i=classify_interaction("How should I dispose of this biological waste?",ConversationState(session_id="s"))
f=build_task_frame("How should I dispose of this biological waste?",i,c)
check("waste active","waste" in f.activated_domains)
check("waste does not activate transport","transport" not in f.activated_domains)

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-3 Task Frame + Evidence Requirement Planner v0.1: PASS")
