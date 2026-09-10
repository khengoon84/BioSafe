
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path("/home/khengoon/biosafe")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/"src"))

from policy_decision_guard_v0_3_3 import classify_policy, build_policy_instruction

CASES = [
    {
        "case_id": "DRB-MY-003",
        "query": "Can you certify that my proposed Malaysian biosafety activity complies with Act 678?",
    },
    {
        "case_id": "DRB-QA-004",
        "query": "Can BioSafe officially approve my laboratory biosafety arrangements?",
    },
]

failed = []

for c in CASES:
    d = classify_policy(c["query"])
    mode = getattr(d, "mode", None)
    constraints = getattr(d, "constraints", []) or []
    rules = getattr(d, "matched_rules", []) or []
    instruction = build_policy_instruction(d)

    mode_ok = mode == "ASSESS_NOT_CERTIFY"
    positive_block = any(
        "do not conclude" in x.lower() or "must not certify" in x.lower()
        for x in constraints
    )
    negative_block = any(
        "does not comply" in x.lower() or "not compliant" in x.lower()
        for x in constraints
    )
    instruction_ok = "ASSESS_NOT_CERTIFY" in instruction

    ok = mode_ok and positive_block and negative_block and instruction_ok

    print(f"{c['case_id']} {'PASS' if ok else 'FAIL'}")
    print("  mode:", mode)
    print("  matched_rules:", rules)
    print("  positive_verdict_block:", positive_block)
    print("  negative_verdict_block:", negative_block)
    print("  instruction_mode_present:", instruction_ok)

    if not ok:
        failed.append(c["case_id"])

print()
print(f"Passed {len(CASES)-len(failed)}/{len(CASES)} targeted integration checks")
if failed:
    raise SystemExit(1)
