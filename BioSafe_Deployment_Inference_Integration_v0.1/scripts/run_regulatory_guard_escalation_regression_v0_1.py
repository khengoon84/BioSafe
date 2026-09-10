
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV01
from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01

def flatten_text(resp):
    parts = []
    for k in ("conclusion","missing_information","recommended_next_step","limitations"):
        v = resp.get(k)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(x) for x in v)
    return " ".join(parts)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT/"output/regulatory_guard_escalation_regression_v0.1_results.json"))
    args = ap.parse_args()

    cases = json.loads((ROOT/"data"/"regulatory_guard_escalation_regression_v0.1.json").read_text(encoding="utf-8"))
    guard = RegulatoryLanguageGuardV01()
    router = ComplexityEscalationRouterV01()
    results = []
    passed = 0

    for c in cases:
        ok = True
        details = {}
        if c["type"] == "regulatory_guard":
            fixed, repairs = guard.apply(c["input"]["response"], c["input"].get("evidence", []))
            text = flatten_text(fixed)
            exp = c["expect"]
            for s in exp.get("not_contains", []):
                if s.lower() in text.lower():
                    ok = False
            for s in exp.get("contains", []):
                if s.lower() not in text.lower():
                    ok = False
            for r in exp.get("repair_contains", []):
                if r not in repairs:
                    ok = False
            for r in exp.get("repair_not_contains", []):
                if r in repairs:
                    ok = False
            details = {"fixed_response": fixed, "repairs": repairs}
        else:
            inp = c["input"]
            routed = router.route(inp["packet"], inp.get("lite_result"))
            exp = c["expect"]
            if routed["model"] != exp["model"]:
                ok = False
            if exp.get("reason") and exp["reason"] not in routed["reasons"]:
                ok = False
            details = routed

        results.append({"id":c["id"], "type":c["type"], "pass":ok, "details":details})
        passed += int(ok)

    out = {
        "suite":"BioSafe_Regulatory_Guard_Escalation_Regression_v0.1",
        "cases":len(cases),
        "passed":passed,
        "failed":len(cases)-passed,
        "results":results
    }
    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"Cases: {len(cases)}")
    print(f"PASS: {passed}")
    print(f"FAIL: {len(cases)-passed}")
    print("Output:", outp)
    if passed != len(cases):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
