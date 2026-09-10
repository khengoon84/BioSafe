
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV01
from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01

class BioSafeDeploymentInferencePolicyV01:
    def __init__(self):
        self.router = ComplexityEscalationRouterV01()
        self.regulatory_guard = RegulatoryLanguageGuardV01()

    def choose_model(self, structured_analysis_packet, lite_result=None):
        return self.router.route(structured_analysis_packet, lite_result)

    def finalize(self, assembled_response, evidence_bundle):
        return self.regulatory_guard.apply(assembled_response, evidence_bundle)
