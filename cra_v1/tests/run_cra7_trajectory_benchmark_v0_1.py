import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))
from trajectory_harness_v0_1 import run_trajectory

cases=json.loads((ROOT/"benchmarks"/"trajectory_cases_v0_1.json").read_text(encoding="utf-8"))
results=[run_trajectory(x) for x in cases]

passed=sum(r.passed for r in results)
assertions=sum(r.assertions_total for r in results)
assertions_passed=sum(r.assertions_passed for r in results)

by_family={}
for r in results:
    by_family.setdefault(r.family,{"passed":0,"total":0})
    by_family[r.family]["total"]+=1
    by_family[r.family]["passed"]+=int(r.passed)

print("BioSafe CRA-7 Conversational Trajectory Benchmark v0.1")
print("="*58)
for r in results:
    print(("PASS" if r.passed else "FAIL"),r.name,f"({r.assertions_passed}/{r.assertions_total})")
    for f in r.failures:
        print("   -",f)

print("\nFamilies")
for family,data in sorted(by_family.items()):
    print(f"{family}: {data['passed']}/{data['total']}")

print(f"\nTrajectory summary: {passed}/{len(results)} passed")
print(f"Assertion summary: {assertions_passed}/{assertions} passed")

report={
    "benchmark":"BioSafe CRA-7 Conversational Trajectory Benchmark v0.1",
    "trajectories_total":len(results),
    "trajectories_passed":passed,
    "assertions_total":assertions,
    "assertions_passed":assertions_passed,
    "families":by_family,
    "results":[{
        "name":r.name,
        "family":r.family,
        "passed":r.passed,
        "assertions_passed":r.assertions_passed,
        "assertions_total":r.assertions_total,
        "failures":r.failures
    } for r in results]
}
out=ROOT/"reports"/"cra7_trajectory_report_v0_1.json"
out.write_text(json.dumps(report,indent=2),encoding="utf-8")
print("Report:",out)

if passed != len(results):
    raise SystemExit(1)
print("\nCRA-7 Conversational Trajectory Benchmark v0.1: PASS")
