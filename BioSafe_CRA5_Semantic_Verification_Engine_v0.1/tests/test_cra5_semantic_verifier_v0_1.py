import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))

from cra_contracts_v0_1 import *
from semantic_verifier_v0_1 import verify_response

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

def base_case():
    c=CaseState(
        case_id="c",
        jurisdiction=FactValue(value="Malaysia",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
    )
    c.facts["lmo_status"]=FactValue(value=None,status=FactStatus.UNKNOWN)
    c.facts["activity_type"]=FactValue(value="routine lab work",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
    return c

def frame(domains=None,expect=None):
    return TaskFrame(
        task_id="t",
        interaction_type=InteractionType.NEW_TASK,
        user_goal="answer_user_question",
        current_question="question",
        jurisdiction="Malaysia",
        activated_domains=list(domains or ["general_biosafety"]),
        inactive_domains=[],
        response_expectations=list(expect or [])
    )

# 1 unresolved prerequisites must not support a substantive decision
d=DecisionNode(
    decision_id="d1",
    decision_type="malaysia_lmo_notification_applicability",
    status=DecisionStatus.SUPPORTED,
    prerequisites=[PrerequisiteResult("lmo_status",False,["lmo_status"])],
    authority_refs=["KB-MY-ACT678"],
    evidence_ids=["E1"],
    reason="bad"
)
res=verify_response(frame(["form_e","lmo_modern_biotechnology"]),base_case(),[d],
                    {"direct_answer":"Form E applies."},
                    {"E1":{"supports_decision_types":["malaysia_lmo_notification_applicability"],"jurisdiction":"Malaysia","status":"current","domains":["form_e"]}})
check("prerequisite insufficiency detected",res.checks["prerequisite_sufficiency"] is False)

# 2 missing evidence support detected
d2=DecisionNode(
    decision_id="d2",
    decision_type="transport_requirement",
    status=DecisionStatus.SUPPORTED,
    prerequisites=[],
    authority_refs=["KB-MY-MOH2023"],
    evidence_ids=["E2"],
    reason="x"
)
res=verify_response(frame(["transport"]),base_case(),[d2],
                    {"direct_answer":"Transport rule applies."},
                    {"E2":{"supports_decision_types":["waste_requirement"],"jurisdiction":"Malaysia","status":"current","domains":["transport"]}})
check("citation entailment mismatch detected",res.checks["citation_support"] is False)

# 3 wrong jurisdiction detected
catalog={"E3":{"supports_decision_types":["transport_requirement"],"jurisdiction":"Singapore","status":"current","domains":["transport"]}}
d3=DecisionNode("d3","transport_requirement",DecisionStatus.SUPPORTED,[],["AUTH"],["E3"],[],"x")
res=verify_response(frame(["transport"]),base_case(),[d3],{"direct_answer":"x"},catalog)
check("wrong jurisdiction detected",res.checks["jurisdiction_match"] is False)

# 4 superseded evidence detected
catalog={"E4":{"supports_decision_types":["transport_requirement"],"jurisdiction":"Malaysia","status":"superseded","domains":["transport"]}}
d4=DecisionNode("d4","transport_requirement",DecisionStatus.SUPPORTED,[],["AUTH"],["E4"],[],"x")
res=verify_response(frame(["transport"]),base_case(),[d4],{"direct_answer":"x"},catalog)
check("superseded source detected",res.checks["currentness"] is False)

# 5 domain leakage detected
catalog={"E5":{"supports_decision_types":["malaysia_lmo_notification_applicability"],"jurisdiction":"Malaysia","status":"current","domains":["form_e"]}}
d5=DecisionNode("d5","malaysia_lmo_notification_applicability",DecisionStatus.SUPPORTED,[],["AUTH"],["E5"],[],"x")
res=verify_response(frame(["general_biosafety"]),base_case(),[d5],{"direct_answer":"x","domains_mentioned":["form_e"]},catalog)
check("domain leakage detected",res.checks["domain_activation"] is False)

# 6 unknown-to-fact promotion detected
c=base_case()
res=verify_response(frame(),c,[],{"direct_answer":"The lmo status is true."},{})
check("unknown promotion detected",res.checks["unknown_preservation"] is False)

# 7 contradiction with confirmed fact detected
c=base_case()
c.facts["lmo_status"]=FactValue(value=False,status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
res=verify_response(frame(),c,[],{"direct_answer":"The lmo status is true."},{})
check("confirmed-fact contradiction detected",res.checks["state_consistency"] is False)

# 8 certification claim blocked
res=verify_response(frame(),base_case(),[],{"direct_answer":"You are compliant with all requirements."},{})
check("compliance certification blocked",res.checks["no_certification"] is False)

# 9 negative compliance verdict also blocked
res=verify_response(frame(),base_case(),[],{"direct_answer":"This is not compliant."},{})
check("negative compliance verdict blocked",res.checks["no_certification"] is False)

# 10 mandatory recommendation without support blocked
res=verify_response(frame(["transport"]),base_case(),[],
                    {"direct_answer":"x","recommended_next_steps":["You must notify the authority."]},{})
check("unsupported mandatory recommendation blocked",res.checks["recommendation_support"] is False)

# 11 supported recommendation passes
catalog={"E6":{"supports_decision_types":["transport_requirement"],"jurisdiction":"Malaysia","status":"current","domains":["transport"],"supports_actions":["use transport packaging guidance"]}}
d6=DecisionNode("d6","transport_requirement",DecisionStatus.SUPPORTED,[],["AUTH"],["E6"],[],"x")
res=verify_response(frame(["transport"]),base_case(),[d6],
                    {"direct_answer":"x","recommended_next_steps":["Use transport packaging guidance."]},catalog)
check("supported recommendation passes",res.checks["recommendation_support"] is True)

# 12 referential follow-up must identify answer target
f=frame(["general_biosafety"],["answer the referenced prior concept directly"])
f.interaction_type=InteractionType.FOLLOW_UP
res=verify_response(f,base_case(),[],{"direct_answer":"Explanation","answer_target":"standalone_new_task"},{})
check("follow-up relevance failure detected",res.checks["turn_relevance"] is False)

res=verify_response(f,base_case(),[],{"direct_answer":"Explanation","answer_target":"referential_follow_up"},{})
check("follow-up relevance passes",res.checks["turn_relevance"] is True)

# 13 clean product help passes all checks
f=TaskFrame(
    task_id="p",
    interaction_type=InteractionType.PRODUCT_HELP,
    user_goal="product_help",
    current_question="What can you review?",
    activated_domains=[],
    inactive_domains=["form_e","transport","waste"],
    response_expectations=["provide product help without regulatory retrieval"]
)
res=verify_response(f,CaseState(case_id="c"),[],
                    {"response_type":"product_help","direct_answer":"I can review SOPs, research proposals and researcher-facing Form E drafts."},{})
check("clean product help passes",res.decision=="PASS")

# 14 valid regulatory response passes
c=base_case()
c.facts["material_identity"]=FactValue(value="clinical specimen",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
catalog={"E7":{"supports_decision_types":["transport_requirement"],"jurisdiction":"Malaysia","status":"current","domains":["transport"],"supports_actions":["consult transport guidance"]}}
d7=DecisionNode("d7","transport_requirement",DecisionStatus.NOT_APPLICABLE,[],["KB-MY-MOH2023"],["E7"],[],"Evidence does not establish the requested transport condition.")
res=verify_response(frame(["transport"]),c,[d7],
                    {"direct_answer":"Based on the stated facts, this transport condition is not established.","recommended_next_steps":["Consult the transport guidance if the transport context changes."],"domains_mentioned":["transport"]},catalog)
check("valid regulatory response passes",res.decision=="PASS")

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-5 Semantic Verification Engine v0.1: PASS")
