import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"examples"))

from cra_contracts_v0_1 import *
from cra_contract_validators_v0_1 import *
import example_contract_objects_v0_1 as ex

checks=[]

def ok(name, fn):
    try:
        fn()
        print("PASS",name)
        checks.append(True)
    except Exception as e:
        print("FAIL",name,"-",e)
        checks.append(False)

ok("product-help interaction", lambda: validate_interaction(ex.product_help))
ok("conversation state", lambda: validate_conversation_state(ex.conversation))
ok("case state", lambda: validate_case_state(ex.case))
ok("task frame", lambda: validate_task_frame(ex.task))
ok("evidence plan", lambda: validate_evidence_plan(ex.evidence))
ok("dependency insufficiency", lambda: validate_decision_node(ex.lmo_decision))
ok("response plan", lambda: validate_response_plan(ex.response))

def bad_unknown_fact():
    validate_fact(FactValue(value="Bacillus anthracis", status=FactStatus.UNKNOWN))
try:
    bad_unknown_fact()
    print("FAIL unknown-fact invariant")
    checks.append(False)
except ContractError:
    print("PASS unknown-fact invariant")
    checks.append(True)

def bad_supported_unsatisfied():
    validate_decision_node(DecisionNode(
        decision_id="x",
        decision_type="test",
        status=DecisionStatus.SUPPORTED,
        prerequisites=[PrerequisiteResult("needed",False,[])],
        reason="bad"
    ))
try:
    bad_supported_unsatisfied()
    print("FAIL prerequisite invariant")
    checks.append(False)
except ContractError:
    print("PASS prerequisite invariant")
    checks.append(True)

def bad_domain_overlap():
    validate_case_state(CaseState(
        case_id="x",
        active_domains=["transport"],
        inactive_domains=["transport"]
    ))
try:
    bad_domain_overlap()
    print("FAIL domain-overlap invariant")
    checks.append(False)
except ContractError:
    print("PASS domain-overlap invariant")
    checks.append(True)

def bad_product_help_sources():
    validate_response_plan(ResponsePlan(
        response_type=ResponseType.PRODUCT_HELP,
        direct_answer="hello",
        source_refs=["CLM-001"]
    ))
try:
    bad_product_help_sources()
    print("FAIL product-help-source invariant")
    checks.append(False)
except ContractError:
    print("PASS product-help-source invariant")
    checks.append(True)

ver=VerificationResult(
    decision="PASS",
    checks={k:True for k in REQUIRED_VERIFIER_CHECKS}
)
ok("verifier complete checks", lambda: validate_verification_result(ver))

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks):
    raise SystemExit(1)
print("CRA-1 Schemas & Deterministic Contracts v0.1: PASS")
