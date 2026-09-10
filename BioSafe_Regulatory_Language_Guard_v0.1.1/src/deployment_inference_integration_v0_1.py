
from __future__ import annotations
from copy import deepcopy

from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV01

class BioSafeDeploymentInferenceIntegrationV01:
    """
    Deployment-oriented integration shell.

    This class does NOT replace the frozen BioSafe core.
    It wraps model selection and final regulatory-language guarding around it.

    Expected pipeline placement:

        Structured Document Analysis v1.0 [FROZEN]
            -> Complexity/Escalation Router v0.1
            -> selected Qwen3.5 runtime
            -> Deterministic Response Assembler v0.1
            -> Regulatory Language Guard v0.1
            -> existing validators
            -> final response
    """

    VERSION = "0.1"

    def __init__(self):
        self.router = ComplexityEscalationRouterV01()
        self.guard = RegulatoryLanguageGuardV01()

    def select_initial_model(self, analysis_packet: dict) -> dict:
        return self.router.route(analysis_packet, lite_result=None)

    def select_after_lite(self, analysis_packet: dict, lite_result: dict) -> dict:
        return self.router.route(analysis_packet, lite_result=lite_result)

    def finalize_response(
        self,
        assembled_response: dict,
        evidence_bundle: list[dict] | None = None,
    ) -> dict:
        guarded, repairs = self.guard.apply(
            deepcopy(assembled_response),
            evidence_bundle or []
        )
        return {
            "response": guarded,
            "integration_repairs": repairs,
            "integration_version": self.VERSION,
        }

    def should_escalate_after_lite(self, route: dict) -> bool:
        return route.get("model") == "qwen3.5:2b"
