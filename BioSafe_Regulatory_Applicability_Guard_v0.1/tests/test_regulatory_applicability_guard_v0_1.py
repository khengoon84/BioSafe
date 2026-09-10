
import sys
from pathlib import Path
PKG=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(PKG/"src"))
from regulatory_applicability_guard_v0_1 import RegulatoryApplicabilityGuardV01

g=RegulatoryApplicabilityGuardV01()
def resp(c):
    return {"conclusion":c,"recommended_next_step":[],"missing_information":[],"limitations":[],"safety":{}}

cases=[]
cases.append(("REG-TRIGGER-001", g.apply(resp("You must notify the Director General under the Biosafety Regulations 2010."), user_query="I am handling Bacillus anthracis.").changed))
cases.append(("REG-TRIGGER-002", g.apply(resp("Notification is required under the Biosafety Regulations."), user_query="I work with Bacillus antracts.").changed))
cases.append(("REG-TRIGGER-003", not g.apply(resp("Prior notification is required for this contained-use LMO activity."), user_query="We use genetically modified E. coli.").changed))
cases.append(("REG-TRIGGER-004", not g.apply(resp("You must notify the Director General for this contained-use activity."), user_query="The project uses a recombinant DNA construct in a genetically modified microorganism.").changed))
cases.append(("REG-TRIGGER-005", g.apply(resp("Form E is required and you must notify the Director General."), user_query="This is a naturally occurring unmodified microorganism and not an LMO.").changed))
cases.append(("REG-TRIGGER-006", not g.apply(resp("A biosafety risk assessment is a systematic process."), user_query="What is biosafety risk assessment?").changed))

failed=[cid for cid,ok in cases if not ok]
for cid,ok in cases:
    print(("PASS" if ok else "FAIL"),cid)
print(f"\nSummary: {len(cases)-len(failed)}/{len(cases)} passed")
if failed:
    raise SystemExit("Failures: "+", ".join(failed))
print("Regulatory Applicability Guard v0.1 regression: PASS")
