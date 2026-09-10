
import sys, json
from pathlib import Path
ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT,ROOT/"src"):
    sys.path.insert(0,str(p))

from full_inference_service_v0_1 import BioSafeFullInferenceServiceV01

svc=BioSafeFullInferenceServiceV01(ROOT)
q="I am working with Bacillus antracts in my laboratory. Do I need to notify the Director General under the Biosafety Regulations?"
r=svc.infer(q,workflow="ask")

print(json.dumps(r,indent=2,ensure_ascii=False))

mi=" | ".join(r.get("missing_information") or []).lower()
recs=" | ".join(r.get("recommended_next_step") or []).lower()

assert "insufficient to determine" in r.get("conclusion","").lower()
assert "confirm the organism name" in mi
assert "living modified organism" in mi
assert "transport category" not in mi
assert "please provide or confirm" in recs
assert r.get("safety",{}).get("response_mode")=="ask_before_concluding"

meta=r.get("_meta",{}).get("decision_quality_refinement",{})
assert meta.get("changed") is True

print("\nDecision Quality Refinement v0.1 live integration regression: PASS")
