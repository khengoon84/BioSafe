import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))

from cra_contracts_v0_1 import *
from interaction_manager_v0_1 import classify_interaction
from state_manager_v0_1 import *
from reference_resolver_v0_1 import resolve_reference
from clarification_resolver_v0_1 import apply_clarification_response
from interaction_state_engine_v0_1 import process_turn

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

state=ConversationState(session_id="s1"); case=CaseState(case_id="c1")

r=classify_interaction("who are you?",state)
check("identity -> product help",r.interaction_type==InteractionType.PRODUCT_HELP and not r.needs_domain_pipeline)

r=classify_interaction("what kind of document can you review?",state)
check("document capability -> product help",r.interaction_type==InteractionType.PRODUCT_HELP and not r.needs_domain_pipeline)

r=classify_interaction("I need advice on biosafety requirements.",state)
check("domain question -> new task",r.interaction_type==InteractionType.NEW_TASK and r.needs_domain_pipeline)

state=add_pending_clarification(state,"organism_identity","Please confirm the organism name.","t1")
r=classify_interaction("Bacillus anthracis",state)
check("short answer -> clarification response",r.interaction_type==InteractionType.CLARIFICATION_RESPONSE)

state,case,resolved=apply_clarification_response(state,case,"Bacillus anthracis","t2")
check("clarification resolved",resolved=="organism_identity")
check("organism fact confirmed",case.facts["organism_identity"].status==FactStatus.USER_CONFIRMED and case.facts["organism_identity"].value=="Bacillus anthracis")
check("clarification removed",len(state.pending_clarifications)==0)

state=add_assistant_concept(state,"concept.notification","Malaysian notification pathway","t3")
r=classify_interaction("what approval did you mean?",state)
check("approval reference -> follow-up",r.interaction_type==InteractionType.FOLLOW_UP)
check("reference resolves",resolve_reference("what approval did you mean?",state)=="concept.notification")

state=add_pending_clarification(state,"lmo_status","Is the material genetically modified?","t4")
state,case,resolved=apply_clarification_response(state,case,"no","t5")
check("boolean clarification resolved",resolved=="lmo_status")
check("LMO false confirmed",case.facts["lmo_status"].value is False and case.facts["lmo_status"].status==FactStatus.USER_CONFIRMED)

case=update_case_fact(case,"activity_type","culture",FactStatus.USER_CONFIRMED,source="user:t6",confidence=1.0)
case=update_case_fact(case,"activity_type","transport",FactStatus.USER_ASSERTED,source="user:t7",confidence=0.8)
check("confirmed fact conflict becomes disputed",case.facts["activity_type"].status==FactStatus.DISPUTED)
check("disputed field reopens question","activity_type" in case.open_questions)

case=set_domains(case,activate=["transport"],deactivate=["general_biosafety"])
check("domain activation","transport" in case.active_domains and "general_biosafety" in case.inactive_domains and "transport" not in case.inactive_domains)

state2=ConversationState(session_id="s2"); case2=CaseState(case_id="c2")
state2=add_pending_clarification(state2,"organism_identity","Confirm organism","t1")
res=process_turn("Bacillus anthracis","t2",state2,case2)
check("engine resolves clarification",res.resolved_clarification_field=="organism_identity")

state3=ConversationState(session_id="s3"); state3=add_assistant_concept(state3,"concept.forme","Form E notification","t1")
case3=CaseState(case_id="c3")
res=process_turn("why?","t2",state3,case3)
check("engine resolves why reference",res.resolved_reference=="concept.forme")

r=classify_interaction("explain that more simply",state3)
check("reformulate recognized",r.interaction_type==InteractionType.REFORMULATE and not r.needs_domain_pipeline)

r=classify_interaction("Actually, I only want to know about transport.",state3)
check("task change recognized",r.interaction_type==InteractionType.TASK_CHANGE)

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-2 Interaction + State Engine v0.1: PASS")
