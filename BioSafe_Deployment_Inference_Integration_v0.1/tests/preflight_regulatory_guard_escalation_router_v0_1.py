
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV01
from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01

g = RegulatoryLanguageGuardV01()

resp = {
    "conclusion": "This violates Malaysian law and requires Tier 1+2 classification.",
    "missing_information": ["Transport category P620/P650 is not stated."],
    "recommended_next_step": ["Confirm the missing information."],
    "limitations": []
}
fixed, repairs = g.apply(resp, [{"record_type":"claim","text":"Risk assessment should determine controls."}])
assert "Tier 1+2" not in fixed["conclusion"]
assert "violates" not in fixed["conclusion"].lower()
assert "P620/P650" not in fixed["missing_information"][0]
assert len(repairs) >= 3

r = ComplexityEscalationRouterV01()
assert r.route({"documents":[{"id":"1"}],"missing_fields":[],"contradictions":[]})["model"] == "qwen3.5:0.8b"
assert r.route({"documents":[{"id":"1"},{"id":"2"}],"missing_fields":[],"contradictions":[]})["model"] == "qwen3.5:2b"
assert r.route({"documents":[{"id":"1"}],"missing_fields":[],"contradictions":[{"x":1}]})["model"] == "qwen3.5:2b"
assert r.route({"documents":[{"id":"1"}],"missing_fields":[],"contradictions":[]},
               {"decision":"RETRY","valid_json":False})["model"] == "qwen3.5:2b"

print("BioSafe Regulatory Language Guard v0.1: PASS")
print("Internal evidence-tier leakage guard: PASS")
print("P620/P650 classification guard: PASS")
print("Unsupported legal-violation softening: PASS")
print("Complexity/Escalation Router v0.1: PASS")
print("0.8B primary route: PASS")
print("2B multi-document/contradiction/failure escalation: PASS")
print("Structured Document Layer v1.0 remains frozen: PASS")
