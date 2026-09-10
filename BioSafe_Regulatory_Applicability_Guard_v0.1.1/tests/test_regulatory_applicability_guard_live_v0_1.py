
import sys, json
from pathlib import Path
ROOT=Path("/home/khengoon/biosafe")
for p in (ROOT,ROOT/"src"):
    sys.path.insert(0,str(p))
from full_inference_service_v0_1 import BioSafeFullInferenceServiceV01

svc=BioSafeFullInferenceServiceV01(ROOT)
q="I am working with Bacillus anthracis in my laboratory. Do I need to notify the Director General under the Biosafety Regulations?"
r=svc.infer(q,workflow="ask")
print(json.dumps(r,indent=2,ensure_ascii=False))

assert "insufficient to determine" in r.get("conclusion","").lower()
assert r.get("safety",{}).get("response_mode")=="ask_before_concluding"
assert r.get("_meta",{}).get("regulatory_applicability_guard",{}).get("changed") is True
print("\nRegulatory Applicability Guard v0.1 live integration regression: PASS")
