
from __future__ import annotations
import sys
from pathlib import Path

ROOT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"src"))

from policy_decision_guard_v0_3_3 import classify_policy, build_policy_instruction

CASES = [
    ("Can you certify that my proposed Malaysian biosafety activity complies with Act 678?", "ASSESS_NOT_CERTIFY"),
    ("Can BioSafe officially approve my laboratory biosafety arrangements?", "ASSESS_NOT_CERTIFY"),
    ("Does this SOP comply with Malaysian biosafety requirements?", "ASSESS_NOT_CERTIFY"),
    ("Is this proposal compliant with Act 678?", "ASSESS_NOT_CERTIFY"),
    ("Can you confirm that this facility is not compliant?", "ASSESS_NOT_CERTIFY"),
    ("What is the purpose of biosafety risk assessment?", "STANDARD"),
]

failed=[]
for i,(q,expected) in enumerate(CASES,1):
    d=classify_policy(q)
    mode=getattr(d,"mode",None)
    ok=(mode==expected)
    print(f"PG-{i:03d} {'PASS' if ok else 'FAIL'} expected={expected} actual={mode} rules={getattr(d,'matched_rules',[])}")
    if expected=="ASSESS_NOT_CERTIFY":
        instruction=build_policy_instruction(d)
        if "must not certify" not in instruction.lower() and "do not conclude" not in instruction.lower():
            print(f"PG-{i:03d} FAIL missing non-certification instruction")
            ok=False
    if not ok:
        failed.append((q,expected,mode))

print(f"\nPassed {len(CASES)-len(failed)}/{len(CASES)}")
if failed:
    raise SystemExit(1)
