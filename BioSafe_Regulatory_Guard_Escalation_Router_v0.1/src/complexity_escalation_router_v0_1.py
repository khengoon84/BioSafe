
from __future__ import annotations

class ComplexityEscalationRouterV01:
    VERSION = "0.1"
    PRIMARY_MODEL = "qwen3.5:0.8b"
    ESCALATION_MODEL = "qwen3.5:2b"

    def route(self, analysis_packet: dict, lite_result: dict | None = None) -> dict:
        reasons = []
        docs = analysis_packet.get("documents") or []
        missing = analysis_packet.get("missing_fields") or []
        contradictions = analysis_packet.get("contradictions") or []

        if len(docs) >= 2:
            reasons.append("MULTI_DOCUMENT")
        if contradictions:
            reasons.append("CROSS_DOCUMENT_CONTRADICTION")
        if len(missing) >= 6:
            reasons.append("HIGH_MISSING_INFORMATION_LOAD")

        if lite_result:
            if lite_result.get("decision") in {"RETRY", "HARD_FAIL"}:
                reasons.append("LITE_GENERATION_FAILURE")
            if lite_result.get("done_reason") == "length":
                reasons.append("LITE_LENGTH_EXHAUSTION")
            if lite_result.get("valid_json") is False:
                reasons.append("LITE_INVALID_OUTPUT")

        # Escalate only for concrete complexity/failure signals.
        model = self.ESCALATION_MODEL if reasons else self.PRIMARY_MODEL
        return {
            "model": model,
            "tier": "complex_case_escalation" if reasons else "primary",
            "reasons": reasons,
            "router_version": self.VERSION,
        }
