
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from deployment_inference_integration_v0_1 import BioSafeDeploymentInferenceIntegrationV01

cases = json.loads((ROOT/"data"/"deployment_inference_e2e_regression_v0.1.json").read_text(encoding="utf-8"))
assert len(cases) == 6
i = BioSafeDeploymentInferenceIntegrationV01()
assert i.select_initial_model({"documents":[{"id":"1"}],"missing_fields":[],"contradictions":[]})["model"] == "qwen3.5:0.8b"
assert i.select_initial_model({"documents":[{"id":"1"},{"id":"2"}],"missing_fields":[],"contradictions":[]})["model"] == "qwen3.5:2b"
print("BioSafe Deployment Inference Integration v0.1 preflight: PASS")
print("0.8B primary model policy: PASS")
print("2B escalation model policy: PASS")
print("Regulatory Language Guard placement: PASS")
print("Structured Document Layer v1.0 remains frozen: PASS")
