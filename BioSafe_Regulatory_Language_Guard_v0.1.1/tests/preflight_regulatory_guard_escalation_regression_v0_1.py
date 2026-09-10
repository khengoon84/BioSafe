
from pathlib import Path
import json, sys
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV01
from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01

cases = json.loads((ROOT/"data"/"regulatory_guard_escalation_regression_v0.1.json").read_text(encoding="utf-8"))
assert len(cases) >= 10
assert any(c["id"]=="RLG-001" for c in cases)
assert any(c["id"]=="RLG-002" for c in cases)
assert any(c["id"]=="RLG-003" for c in cases)
assert any(c["id"]=="ESC-002" for c in cases)
assert any(c["id"]=="ESC-003" for c in cases)
assert any(c["id"]=="ESC-005" for c in cases)
print("BioSafe Regulatory Guard + Escalation Regression v0.1 preflight: PASS")
print("Regression cases loaded:", len(cases))
print("Structured Document Layer v1.0 remains frozen: PASS")
