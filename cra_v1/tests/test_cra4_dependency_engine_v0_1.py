import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))

from cra_contracts_v0_1 import *
from dependency_decision_engine_v0_1 import *

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

def my_case():
    return CaseState(
        case_id="c",
        jurisdiction=FactValue(value="Malaysia",status=FactStatus.USER_CONFIRMED,source="user",confidence=1.0)
    )

# 1 species alone cannot establish LMO notification readiness
c=my_case()
c.facts["organism_identity"]=FactValue(value="Bacillus anthracis",status=FactStatus.USER_CONFIRMED,source="user",confidence=1.0)
d=evaluate_decision_readiness("malaysia_lmo_notification_applicability",c)
check("species alone -> insufficient",d.status==DecisionStatus.INSUFFICIENT_INFORMATION)
check("LMO status unresolved","lmo_status" in d.unresolved_dependencies)
check("activity unresolved","activity_type" in d.unresolved_dependencies)

# 2 inferred LMO status cannot satisfy prerequisite
c.facts["lmo_status"]=FactValue(value=True,status=FactStatus.INFERRED,source="species inference",confidence=.8)
c.facts["activity_type"]=FactValue(value="contained use",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
d=evaluate_decision_readiness("malaysia_lmo_notification_applicability",c)
check("inferred LMO does not satisfy","lmo_status" in d.unresolved_dependencies)

# 3 user-asserted but unconfirmed status also cannot satisfy
c.facts["lmo_status"]=FactValue(value=True,status=FactStatus.USER_ASSERTED,source="user",confidence=.7)
d=evaluate_decision_readiness("malaysia_lmo_notification_applicability",c)
check("unconfirmed assertion does not satisfy","lmo_status" in d.unresolved_dependencies)

# 4 confirmed LMO false is an established prerequisite fact, but does not itself mean notification applies
c.facts["lmo_status"]=FactValue(value=False,status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
d=evaluate_decision_readiness("malaysia_lmo_notification_applicability",c)
check("confirmed false counts as established fact",d.status==DecisionStatus.REQUIRES_HUMAN_REVIEW)
check("readiness is not substantive applicability",d.status!=DecisionStatus.SUPPORTED)

# 5 cannot turn unresolved readiness into substantive rule
c2=my_case()
r=evaluate_decision_readiness("malaysia_lmo_notification_applicability",c2)
try:
    apply_supported_rule(r,"supported",["KB-MY-ACT678"],["CLM-1"],"test")
    check("unresolved blocks substantive rule",False)
except DependencyEngineError:
    check("unresolved blocks substantive rule",True)

# 6 substantive rule requires evidence and authority
c3=my_case()
c3.facts["lmo_status"]=FactValue(value=False,status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
c3.facts["activity_type"]=FactValue(value="culture",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
r=evaluate_decision_readiness("malaysia_lmo_notification_applicability",c3)
try:
    apply_supported_rule(r,"not_applicable",[],[],"No LMO trigger established.")
    check("authority/evidence required",False)
except DependencyEngineError:
    check("authority/evidence required",True)

# 7 with authority/evidence a rule can produce a decision
d=apply_supported_rule(r,"not_applicable",["KB-MY-ACT678"],["CLM-LMO-DEF"],"Confirmed facts do not establish an LMO trigger for this decision path.")
check("supported rule produces not-applicable",d.status==DecisionStatus.NOT_APPLICABLE)
check("decision preserves evidence",d.evidence_ids==["CLM-LMO-DEF"])

# 8 containment basic readiness needs identity + activity
c4=my_case()
c4.facts["organism_identity"]=FactValue(value="Example organism",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
d=evaluate_decision_readiness("containment_assessment",c4)
check("containment needs activity","activity_or_procedure" in d.unresolved_dependencies)

c4.facts["activity_type"]=FactValue(value="routine laboratory handling",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
d=evaluate_decision_readiness("containment_assessment",c4)
check("basic containment prerequisites established",d.status==DecisionStatus.REQUIRES_HUMAN_REVIEW)

# 9 specific containment requires more context
d=evaluate_decision_readiness("containment_assessment",c4,specific=True)
check("specific containment needs exposure","exposure_route" in d.unresolved_dependencies)
check("specific containment needs scale","scale_or_quantity" in d.unresolved_dependencies)
check("specific containment needs facility","facility_context" in d.unresolved_dependencies)

# 10 risk group alone is not a containment prerequisite substitute
c5=my_case()
c5.facts["risk_group"]=FactValue(value="RG3",status=FactStatus.AUTHORITY_DERIVED,source="authority",confidence=1)
d=evaluate_decision_readiness("containment_assessment",c5)
check("risk group alone insufficient",d.status==DecisionStatus.INSUFFICIENT_INFORMATION)

# 11 transport requires material + transport context
c6=my_case()
c6.facts["material_identity"]=FactValue(value="clinical specimen",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
d=evaluate_decision_readiness("transport_requirement",c6)
check("transport context required","transport_context" in d.unresolved_dependencies)

# 12 organism mention does not create transport readiness
c7=my_case()
c7.facts["organism_identity"]=FactValue(value="Example organism",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
d=evaluate_decision_readiness("transport_requirement",c7)
check("organism can establish material identity", "material_identity" not in d.unresolved_dependencies)
check("transport still unresolved without context","transport_context" in d.unresolved_dependencies)

# 13 waste needs waste type and disposal context
c8=my_case()
d=evaluate_decision_readiness("waste_requirement",c8)
check("waste type required","waste_type" in d.unresolved_dependencies)
check("disposal context required","disposal_context" in d.unresolved_dependencies)

# 14 disputed facts never satisfy
c9=my_case()
c9.facts["waste_type"]=FactValue(value=None,status=FactStatus.DISPUTED,source="conflict")
c9.facts["disposal_context"]=FactValue(value="on-site",status=FactStatus.USER_CONFIRMED,source="user",confidence=1)
d=evaluate_decision_readiness("waste_requirement",c9)
check("disputed fact remains unresolved","waste_type" in d.unresolved_dependencies)

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-4 Dependency Decision Engine v0.1: PASS")
