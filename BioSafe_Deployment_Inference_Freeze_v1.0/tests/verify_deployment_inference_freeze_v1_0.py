
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
freeze = json.loads((ROOT/"data"/"BioSafe_Deployment_Inference_Layer_v1.0_FREEZE.json").read_text(encoding="utf-8"))
bench = json.loads((ROOT/"data"/"BioSafe_Deployment_Readiness_Benchmark_v0.1.json").read_text(encoding="utf-8"))

assert freeze["status"] == "FROZEN"
assert freeze["components"]["regulatory_language_guard"]["version"] == "v0.1.1"
assert freeze["components"]["complexity_escalation_router"]["version"] == "v0.1"
assert freeze["components"]["complexity_escalation_router"]["primary_model"] == "qwen3.5:0.8b"
assert freeze["components"]["complexity_escalation_router"]["escalation_model"] == "qwen3.5:2b"
assert sum(x["count"] for x in bench["case_groups"]) == 24
assert bench["acceptance_gate"]["hard_gate_failures"] == 0

print("BioSafe Deployment Inference Layer v1.0 freeze verification: PASS")
print("Regulatory Language Guard v0.1.1 frozen: PASS")
print("Complexity/Escalation Router v0.1 frozen: PASS")
print("Qwen3.5-0.8B primary policy: PASS")
print("Qwen3.5-2B escalation policy: PASS")
print("Deployment Readiness Benchmark v0.1 specification: PASS")
