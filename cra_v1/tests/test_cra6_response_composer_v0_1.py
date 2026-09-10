import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))

from cra_contracts_v0_1 import *
from researcher_response_composer_v0_1 import *

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

PASS_VER=VerificationResult(
    decision="PASS",
    checks={
        "prerequisite_sufficiency":True,
        "citation_support":True,
        "jurisdiction_match":True,
        "currentness":True,
        "domain_activation":True,
        "state_consistency":True,
        "unknown_preservation":True,
        "no_certification":True,
        "recommendation_support":True,
        "turn_relevance":True,
    }
)

def frame():
    return TaskFrame(
        task_id="t",
        interaction_type=InteractionType.NEW_TASK,
        user_goal="answer_user_question",
        current_question="question",
        jurisdiction="Malaysia",
        activated_domains=["general_biosafety"]
    )

# 1 insufficient info -> needs clarification
d=DecisionNode(
    decision_id="d1",
    decision_type="malaysia_lmo_notification_applicability",
    status=DecisionStatus.INSUFFICIENT_INFORMATION,
    prerequisites=[],
    unresolved_dependencies=["lmo_status","activity_type"],
    reason="missing"
)
p=compose_response_plan(frame(),[d],PASS_VER)
check("insufficient -> needs clarification",p.response_type==ResponseType.NEEDS_CLARIFICATION)
check("clarification questions generated",len(p.clarification_questions)==2)
check("species-independent teaching point",any("organism name alone" in x for x in p.why_this_matters))

# 2 duplicate clarification not repeated as next step
p=compose_response_plan(
    frame(),[d],PASS_VER,
    recommended_next_steps=[
        "Is the material genetically modified, recombinant, or otherwise produced using modern biotechnology?",
        "Confirm the modification status before continuing."
    ]
)
check("clarification deduped from next steps",len(p.recommended_next_steps)==1)

# 3 product help has no evidence refs
p=compose_response_plan(
    frame(),[],PASS_VER,
    product_help=True,
    direct_answer_hint="I can review SOPs, proposals and researcher-facing Form E drafts.",
    source_refs=["KB-MY-GMMRA"]
)
check("product help type",p.response_type==ResponseType.PRODUCT_HELP)
check("product help hides evidence",p.source_refs==[])

# 4 regulatory not-applicable answer
d2=DecisionNode(
    decision_id="d2",
    decision_type="malaysia_lmo_notification_applicability",
    status=DecisionStatus.NOT_APPLICABLE,
    prerequisites=[],
    authority_refs=["KB-MY-ACT678"],
    evidence_ids=["E1"],
    reason="not activated"
)
p=compose_response_plan(frame(),[d2],PASS_VER,source_refs=["KB-MY-ACT678"])
check("regulatory assessment type",p.response_type==ResponseType.REGULATORY_ASSESSMENT)
check("not-applicable direct answer","not activated" in p.direct_answer)
check("sources retained",p.source_refs==["KB-MY-ACT678"])

# 5 document review type
p=compose_response_plan(frame(),[],PASS_VER,document_review=True)
check("document review type",p.response_type==ResponseType.DOCUMENT_REVIEW)

# 6 form E type
p=compose_response_plan(frame(),[],PASS_VER,form_e=True)
check("form E type",p.response_type==ResponseType.FORM_E_ASSIST)

# 7 safety redirect no evidence
p=compose_response_plan(frame(),[],PASS_VER,safety_redirect=True,source_refs=["X"])
check("safety redirect type",p.response_type==ResponseType.SAFETY_REDIRECT)
check("safety redirect hides evidence",p.source_refs==[])

# 8 failed verification blocks composition
FAIL_VER=VerificationResult(
    decision="FAIL",
    checks={k:False for k in PASS_VER.checks},
    issues=["x"]
)
try:
    compose_response_plan(frame(),[],FAIL_VER)
    check("failed verification blocks composer",False)
except ResponseCompositionError:
    check("failed verification blocks composer",True)

# 9 rendering is conditional, not rigid
p=compose_response_plan(
    frame(),[d2],PASS_VER,
    direct_answer_hint="This pathway is not activated.",
    educational_points=["This matters because the trigger condition is not established."],
    source_refs=["KB-MY-ACT678"]
)
r=render_response(p)
keys=[x["key"] for x in r["sections"]]
check("render includes why when useful","why_this_matters" in keys)
check("render omits clarification when absent","what_i_need" not in keys)
check("render includes collapsed sources","sources" in keys and [x for x in r["sections"] if x["key"]=="sources"][0]["collapsed"] is True)

# 10 no developer metadata in rendered response
check("no developer metadata","_meta" not in r and "developer" not in r)

# 11 explanation and evidence separated
source_section=[x for x in r["sections"] if x["key"]=="sources"][0]
why_section=[x for x in r["sections"] if x["key"]=="why_this_matters"][0]
check("explanation not same as sources",why_section["items"]!=source_section["items"])

# 12 no forced sections for simple answer
simple=compose_response_plan(frame(),[],PASS_VER,direct_answer_hint="BioSafe is a local biosafety assistant.")
rendered=render_response(simple)
check("simple answer has no empty sections",rendered["sections"]==[])

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-6 Researcher Response Composer v0.1: PASS")
