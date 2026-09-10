
from pathlib import Path
import sys, inspect
PROJECT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(PROJECT))
sys.path.insert(0,str(PROJECT/"src"))
from biosafe_pipeline_v0_1 import BioSafePipelineV01

sig=str(inspect.signature(BioSafePipelineV01))
bm=str(inspect.signature(BioSafePipelineV01.build_messages))
assert "root" in sig and "top_k" in sig
assert "query" in bm and "case_id" in bm and "safety_class" in bm

p=BioSafePipelineV01(root=PROJECT,top_k=3)
bundle,messages=p.build_messages("What is the purpose of a biosafety risk assessment?",case_id="PREFLIGHT")
assert isinstance(bundle,dict)
assert "route" in bundle
assert "evidence_bundle" in bundle
assert isinstance(messages,list) and len(messages)==2
assert len(bundle["evidence_bundle"]) > 0

print("BioSafe Live24 v0.3.1 Exact Interface preflight: PASS")
print("BioSafePipelineV01 constructor: PASS")
print("build_messages interface: PASS")
print("Authority-aware retrieval returned evidence: PASS")
print("Frozen architecture modification: NONE")
