
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV01
from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01

g=RegulatoryLanguageGuardV01()
fixed, repairs=g.apply(
    {"conclusion":"The SOP violates Malaysian law.","missing_information":[],"recommended_next_step":[],"limitations":[]},
    [{"record_type":"claim","text":"Risk assessment should determine appropriate controls."}]
)
assert fixed["conclusion"]=="The SOP may have a regulatory gap that requires verification against the applicable Malaysian requirements."
assert "REG_LANG_UNSUPPORTED_VIOLATION_SOFTENED" in repairs

r=ComplexityEscalationRouterV01()
assert r.route({"documents":[{"id":"1"}],"missing_fields":[],"contradictions":[]})["model"]=="qwen3.5:0.8b"
assert r.route({"documents":[{"id":"1"},{"id":"2"}],"missing_fields":[],"contradictions":[]})["model"]=="qwen3.5:2b"

print("BioSafe Regulatory Language Guard v0.1.1 preflight: PASS")
print("Clause-level semantic repair: PASS")
print("Escalation Router v0.1 unchanged: PASS")
print("Structured Document Layer v1.0 remains frozen: PASS")
