import sys, json
from pathlib import Path
ROOT=Path('/home/khengoon/biosafe')
for p in (ROOT,ROOT/'src'):
    sys.path.insert(0,str(p))
from full_inference_service_v0_1 import BioSafeFullInferenceServiceV01

svc=BioSafeFullInferenceServiceV01(ROOT)
q='I am working with Bacillus antracts in my laboratory. Do I need to notify the Director General under the Biosafety Regulations?'
r=svc.infer(q,workflow='ask')
print(json.dumps(r,indent=2,ensure_ascii=False))
combined=' '.join([r.get('conclusion',''),*(r.get('recommended_next_step') or [])]).lower()
mi=' | '.join(r.get('missing_information') or []).lower()
assert 'class 1.5' not in combined
assert 'bacillus anthracis is' not in combined
assert 'confirm the organism name' in mi
assert r.get('safety',{}).get('response_mode')=='ask_before_concluding'
print('\nDecision Quality Refinement v0.1.3 live regression: PASS')
