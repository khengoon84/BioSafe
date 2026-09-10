
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from deployment_inference_integration_v0_1 import BioSafeDeploymentInferenceIntegrationV01

def flatten(resp):
    parts = []
    for k in ("conclusion","missing_information","recommended_next_step","limitations"):
        v = resp.get(k)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(x) for x in v)
    return " ".join(parts)

def main():
    cases = json.loads((ROOT/"data"/"deployment_inference_e2e_regression_v0.1.json").read_text(encoding="utf-8"))
    integ = BioSafeDeploymentInferenceIntegrationV01()
    results = []
    passed = 0

    for c in cases:
        ok = True
        initial = integ.select_initial_model(c["packet"])
        after = None
        if c.get("lite_result") is not None:
            after = integ.select_after_lite(c["packet"], c["lite_result"])

        final = integ.finalize_response(c["assembled"], c.get("evidence", []))
        text = flatten(final["response"])
        exp = c["expect"]

        if exp.get("initial") and initial["model"] != exp["initial"]:
            ok = False
        if exp.get("after") and (after is None or after["model"] != exp["after"]):
            ok = False
        for s in exp.get("not_contains", []):
            if s.lower() in text.lower():
                ok = False
        if exp.get("repair") and exp["repair"] not in final["integration_repairs"]:
            ok = False

        results.append({
            "id":c["id"],
            "scenario":c["scenario"],
            "pass":ok,
            "initial_route":initial,
            "after_lite_route":after,
            "integration_repairs":final["integration_repairs"],
            "final_response":final["response"]
        })
        passed += int(ok)

    out = {
        "suite":"BioSafe_Deployment_Inference_E2E_Regression_v0.1",
        "cases":len(cases),
        "passed":passed,
        "failed":len(cases)-passed,
        "results":results
    }
    outdir = ROOT/"output"
    outdir.mkdir(exist_ok=True)
    outfile = outdir/"deployment_inference_e2e_regression_v0.1_results.json"
    outfile.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Cases: {len(cases)}")
    print(f"PASS: {passed}")
    print(f"FAIL: {len(cases)-passed}")
    print("Output:", outfile)
    if passed != len(cases):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
