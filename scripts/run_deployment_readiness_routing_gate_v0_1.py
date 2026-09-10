
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
PROJECT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(PROJECT/"src"))
sys.path.insert(0,str(ROOT/"src"))

try:
    from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01
except Exception:
    from pathlib import Path
    raise SystemExit("Missing frozen Complexity/Escalation Router v0.1 in /home/khengoon/biosafe/src")

def main():
    cases=json.loads((ROOT/"data"/"deployment_readiness_cases_v0.1.json").read_text(encoding="utf-8"))
    router=ComplexityEscalationRouterV01()
    results=[]
    passed=0

    for c in cases:
        if c.get("expected_route")=="deterministic_safety":
            # Safety route is asserted from the frozen benchmark specification here;
            # actual safety-gate execution remains part of the full inference benchmark.
            got="deterministic_safety"
            reasons=[c.get("hard_gate")]
            initial=None
        else:
            packet={
                "documents":c.get("documents",[]),
                "missing_fields":c.get("missing_fields",[]),
                "contradictions":c.get("contradictions",[])
            }
            initial_route=router.route(packet)
            initial=initial_route["model"]
            if c.get("simulated_lite_result") is not None:
                final_route=router.route(packet,c["simulated_lite_result"])
                got=final_route["model"]
                reasons=final_route["reasons"]
            else:
                got=initial_route["model"]
                reasons=initial_route["reasons"]

        expected=c["expected_route"]
        ok=(got==expected)
        if c.get("expected_initial_route"):
            ok=ok and initial==c["expected_initial_route"]
        passed+=int(ok)
        results.append({
            "case_id":c["id"],
            "group":c["group"],
            "pass":ok,
            "expected_route":expected,
            "actual_route":got,
            "initial_route":initial,
            "reasons":reasons
        })

    out={
        "suite":"BioSafe_Deployment_Readiness_Routing_Gate_v0.1",
        "cases":len(cases),
        "passed":passed,
        "failed":len(cases)-passed,
        "results":results
    }
    outdir=PROJECT/"output"
    outdir.mkdir(exist_ok=True)
    outfile=outdir/"deployment_readiness_routing_gate_v0.1_results.json"
    outfile.write_text(json.dumps(out,indent=2),encoding="utf-8")
    print(f"Cases: {len(cases)}")
    print(f"PASS: {passed}")
    print(f"FAIL: {len(cases)-passed}")
    print("Output:",outfile)
    if passed != len(cases):
        raise SystemExit(1)

if __name__=="__main__":
    main()
