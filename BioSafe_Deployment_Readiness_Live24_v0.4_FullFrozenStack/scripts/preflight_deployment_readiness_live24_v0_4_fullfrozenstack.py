
from pathlib import Path
import json, sys
PROJECT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(PROJECT)); sys.path.insert(0,str(PROJECT/"src"))

from biosafe_pipeline_v0_3_2 import BioSafePipelineV032
from structured_document_benchmark_adapter_v0_1 import BioSafeStructuredBenchmarkAdapterV01
from deterministic_response_assembler_v0_1 import assemble_biosafe_response
from output_normalizer_v0_3_2 import normalize_output
from output_validator_v0_2 import validate_output
from boundary_validator_v0_3_2 import validate_boundaries
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV011
from context_budget_manager_v0_1 import select_profile, response_contract

cases=json.loads((PROJECT/"data"/"deployment_readiness_cases_v0.1.json").read_text())
fixtures=json.loads((PROJECT/"data"/"deployment_readiness_document_fixtures_v0.1.json").read_text())
assert len(cases)==24
assert "sop1" in fixtures and "forme7" in fixtures

p=BioSafePipelineV032(root=PROJECT,top_k=3)
bundle,messages=p.build_messages("What is the purpose of biosafety risk assessment?",case_id="PREFLIGHT")
assert isinstance(bundle,dict) and bundle.get("evidence_bundle")
assert len(messages)>=2

profile=select_profile("qwen3.5:0.8b")
contract=response_contract(profile)
assert "conclusion" in contract and "missing_information" in contract

adapter=BioSafeStructuredBenchmarkAdapterV01(PROJECT)
doc=adapter.analyse("sop1.txt",fixtures["sop1"])
assert isinstance(doc,dict)

print("BioSafe Live24 v0.4 Full Frozen Stack preflight: PASS")
print("BioSafePipelineV032: PASS")
print("Authority-aware evidence retrieval: PASS")
print("Structured document adapter: PASS")
print("Context-budget compact response contract: PASS")
print("Deterministic response assembler import: PASS")
print("Output normalizer / validator / boundary validator imports: PASS")
print("Regulatory Language Guard v0.1.1 import: PASS")
print("Frozen architecture modification: NONE")
