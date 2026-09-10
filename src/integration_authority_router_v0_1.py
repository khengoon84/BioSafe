from __future__ import annotations
from typing import List

from scope_gate_v0_2_1 import BioSafeCFG02ScopeV021
from router_v02 import Route, norm, has_any


class BioSafeIntegrationAuthorityRouterV01(BioSafeCFG02ScopeV021):
    """
    Generation-layer authority router v0.1.

    Preserves the frozen CFG-02 ranking formula, Router v0.2 and Scope Gate
    v0.2.1. It only adds WHO-first routing for generic biosafety concepts when
    the user has not asked about Malaysian jurisdiction/regulation.
    """

    MALAYSIA_SIGNALS: List[str] = [
        "malaysia", "malaysian", "biosafety act", "act 678", "form e",
        "lmo", "living modified organism", "gmm", "genetically modified",
        "notification", "department of biosafety", "ibc", "institutional biosafety",
        "sw 404", "scheduled waste", "clinical specimen", "infectious substance"
    ]

    def classify(self, query: str) -> Route:
        frozen = super().classify(query)
        q = norm(query)

        # Never override explicit Malaysian/regulatory/special-domain intent.
        if has_any(q, self.MALAYSIA_SIGNALS):
            return frozen

        ppe = has_any(q, [
            "ppe", "personal protective equipment", "gloves", "laboratory coat",
            "lab coat", "eye protection", "respiratory protection"
        ])
        hazard_risk = (
            has_any(q, ["difference", "distinguish", "versus", " vs "])
            and has_any(q, ["hazard", "risk"])
        )
        control_selection = has_any(q, [
            "what biosafety controls", "what controls", "controls are appropriate",
            "control measures are appropriate", "decide what biosafety controls",
            "select controls", "select control measures"
        ])
        risk_assessment = has_any(q, [
            "biological risk assessment", "biosafety risk assessment",
            "laboratory risk assessment", "risk assessment before",
            "performing a biosafety risk assessment", "perform risk assessment"
        ])

        if not any([ppe, hazard_risk, control_selection, risk_assessment]):
            return frozen

        if ppe:
            intent="ppe_limits"
            scope=["PPE","personal protective equipment","risk assessment",
                   "core requirements","risk control measures","layered controls"]
            expansion=("PPE personal protective equipment not alone core requirements "
                       "risk assessment control measures training equipment containment")
        elif hazard_risk:
            intent="hazard_risk"
            scope=["hazard","risk","likelihood","consequence","context"]
            expansion=("biological hazard potential harm biological risk likelihood "
                       "exposure release consequence severity laboratory context")
        elif control_selection:
            intent="control_selection"
            scope=["risk assessment","risk control measures","residual risk",
                   "activity specific","PPE","equipment","containment"]
            expansion=("select implement risk control measures activity specific "
                       "risk assessment residual risk available effective sustainable "
                       "training PPE equipment containment")
        else:
            intent="risk_assessment"
            scope=["risk assessment","hazard","likelihood","consequence",
                   "activity specific","procedures","equipment","facility","competency"]
            expansion=("systematic biological risk assessment gather information evaluate risks "
                       "hazards likelihood consequences procedures equipment facility competency "
                       "activity specific inform risk control measures")

        return Route(
            jurisdiction="International",
            domain="WHO-RA",
            intent=intent,
            preferred_tier="Tier 3",
            scope=scope,
            uncertainty_sensitive=False,
            safety_sensitive=False,
            expansion_terms=expansion,
            rationale="Generic biosafety concept without Malaysian jurisdiction: WHO-first generation route."
        )

    def _eligible(self, r, p):
        if p.domain == "WHO-RA" and p.intent in {
            "risk_assessment", "hazard_risk", "control_selection", "ppe_limits"
        }:
            if r["record_type"] == "control_rule":
                return False
            return r["document_id"] in {"KB-WHO-RA", "KB-WHO-LBM4", "KB-WHO-PPE"}
        return super()._eligible(r, p)

    def _expand_query(self, query, p):
        expanded = super()._expand_query(query, p)
        if p.domain == "WHO-RA" and p.intent in {
            "risk_assessment", "hazard_risk", "control_selection", "ppe_limits"
        }:
            expanded += " " + p.expansion_terms
        return expanded
