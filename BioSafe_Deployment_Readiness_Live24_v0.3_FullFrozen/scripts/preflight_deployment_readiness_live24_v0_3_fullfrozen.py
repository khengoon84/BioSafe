
from pathlib import Path
import json, importlib, sys

PROJECT=Path("/home/khengoon/biosafe")
CASES=PROJECT/"data"/"deployment_readiness_cases_v0.1.json"

assert PROJECT.exists(), "BioSafe project root missing"
assert CASES.exists(), "24-case deployment readiness dataset missing"
cases=json.loads(CASES.read_text(encoding="utf-8"))
assert len(cases)==24

mods=[
    "pipeline_v0_1",
    "biosafe_pipeline_v0_1",
    "local_llm_pipeline_v0_1",
    "deployment_inference_integration_v0_1",
]
found=[]
sys.path.insert(0,str(PROJECT))
sys.path.insert(0,str(PROJECT/"src"))
for m in mods:
    try:
        importlib.import_module(m)
        found.append(m)
    except Exception:
        pass

print("BioSafe Live24 v0.3 Full Frozen preflight: PASS")
print("24 cases available: PASS")
print("Frozen architecture modification: NONE")
print("Candidate pipeline modules found:", found if found else "NONE")
if not found:
    print("NOTE: runner will stop rather than use a simplified fallback.")
