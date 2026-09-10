#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

@dataclass
class PolicyDecision:
    short_circuit: bool
    mode: str
    constraints: List[str]
    reason: str
    matched_rules: List[str]
    deterministic_response: Dict[str, Any] | None = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _match_any(q: str, patterns: List[str]) -> bool:
    return any(re.search(p, q, flags=re.I | re.S) for p in patterns)


def _restricted_bio_request(q: str) -> tuple[bool, List[str]]:
    rules = []
    patterns = {
        "increase_harmful_capability": [
            r"\bincrease\b.{0,40}\b(infectivity|pathogenicity|virulence)\b",
            r"\bmake\b.{0,50}\b(more infectious|more pathogenic|more virulent|more harmful)\b",
            r"\benhance\b.{0,40}\b(infectivity|pathogenicity|virulence)\b",
        ],
        "defeat_containment": [
            r"\b(overcome|defeat|bypass|evade|circumvent)\b.{0,50}\bcontainment\b",
            r"\bdefeat\b.{0,50}\b(laboratory|lab)\b.{0,30}\bsecurity\b",
        ],
        "actionable_harmful_modification": [
            r"\b(detailed|step[- ]by[- ]step|procedure|protocol|method)\b.{0,80}\b(modif|engineer|alter)\w*\b.{0,80}\b(biological|pathogen|agent)\b",
            r"\b(modif|engineer|alter)\w*\b.{0,80}\b(biological|pathogen|agent)\b.{0,80}\b(overcome|defeat|bypass|evade|circumvent)\b",
        ],
    }
    for label, ps in patterns.items():
        if _match_any(q, ps):
            rules.append(label)
    return bool(rules), rules


def _deterministic_refusal(reason: str) -> Dict[str, Any]:
    return {
        "conclusion": (
            "I can help assess biosafety or biosecurity risk, but I cannot provide "
            "instructions for increasing harmful biological capability or defeating containment."
        ),
        "applicable_authority": [
            "BioSafe safety policy"
        ],
        "evidence": [],
        "missing_information": [],
        "recommended_next_step": [
            "Use a non-operational risk assessment focused on hazards, exposure routes, containment layers and consequences.",
            "Use authorised vulnerability assessment or security testing procedures under appropriate institutional governance.",
            "Escalate the assessment to the responsible biosafety or biosecurity authority when needed."
        ],
        "limitations": [
            "Operational methods, parameters, optimisation advice and troubleshooting that could enable harmful biological modification or containment defeat are withheld."
        ],
        "safety": {
            "classification": "refusal",
            "response_mode": "refuse_and_redirect",
            "reason": reason
        }
    }


def classify_policy(query: str) -> PolicyDecision:
    q = (query or "").strip()
    ql = q.lower()

    restricted, restricted_rules = _restricted_bio_request(ql)
    if restricted:
        reason = "Request may enable harmful biological capability or defeat containment."
        return PolicyDecision(
            short_circuit=True,
            mode="DETERMINISTIC_REFUSAL",
            constraints=[
                "Do not send the restricted request to the generative model.",
                "Do not provide operational methods, parameters, optimisation or troubleshooting.",
                "Redirect to non-operational risk assessment, authorised testing and governance."
            ],
            reason=reason,
            matched_rules=restricted_rules,
            deterministic_response=_deterministic_refusal(reason),
        )

    constraints: List[str] = []
    matched: List[str] = []
    modes: List[str] = []

    # PPE / layered controls
    if (
        "ppe" in ql
        and _match_any(ql, [
            r"\b(can|could|may)\b.{0,40}\b(consider|call|say)\b.{0,40}\b(safe|biosafe)\b",
            r"\bppe\b.{0,50}\b(enough|sufficient|safe)\b",
        ])
    ):
        matched.append("PPE_LAYERED_CONTROL")
        modes.append("LAYERED_CONTROL")
        constraints.append(
            "PPE alone must never be used to conclude that a biological activity is safe; frame PPE as one layer selected through risk assessment."
        )

    # General safety / biosafety determination with insufficient scenario detail.
    if "PPE_LAYERED_CONTROL" not in matched and _match_any(ql, [
        r"\b(can you|could you|please)\b.{0,50}\b(assess|decide|determine)\b.{0,35}\b(biosafe|safe)\b",
        r"\bis (this|my|the)\b.{0,40}\b(biosafe|safe)\b",
        r"\bcan i consider\b.{0,50}\b(safe|biosafe)\b",
    ]):
        matched.append("SAFETY_DETERMINATION_BOUNDARY")
        modes.append("ASK_BEFORE_SAFETY_CONCLUSION")
        constraints.extend([
            "Do not declare an activity safe or unsafe when the user has not supplied enough activity-specific information.",
            "Identify the missing facts needed for assessment, including material/hazard, procedures, scale, exposure routes, facility/containment, personnel and waste; include transport/storage when relevant.",
            "Use wording such as 'insufficient information to determine' rather than certifying safety."
        ])

    # Compliance / approval / certification boundary.
    if _match_any(ql, [
        r"\b(confirm|certify|declare|decide|determine)\b.{0,50}\b(compliant|compliance|approved|approval)\b",
        r"\b(is|are)\b.{0,40}\b(compliant|approved)\b",
        r"\blegally compliant\b",
    ]):
        matched.append("ASSESS_NOT_CERTIFY")
        modes.append("ASSESS_NOT_CERTIFY")
        constraints.extend([
            "BioSafe may assess apparent alignment and identify gaps, but must not certify compliance or approval.",
            "Do not state that a project, activity, facility or submission is officially compliant, non-compliant, approved or rejected.",
            "Reserve official determinations for authorised institutional or regulatory bodies."
        ])

    # Malaysian Form E scope / legal determination.
    if "form e" in ql:
        if _match_any(ql, [
            r"\bevery\b.{0,50}\b(lab|laboratory)\b",
            r"\ball\b.{0,50}\b(lab|laborator|biological)\b",
            r"\b(need|required|requires|require)\b.{0,30}\bform e\b",
            r"\bform e\b.{0,40}\b(need|required|requires|require)\b",
            r"\bdecide\b.{0,50}\blegally requires?\b",
            r"\blegally requires?\b.{0,40}\bform e\b",
        ]):
            matched.append("FORM_E_SCOPE_BOUNDARY")
            modes.append("LIKELY_PATHWAY_NOT_LEGAL_DETERMINATION")
            constraints.extend([
                "Do not state that every laboratory working with biological material requires Form E.",
                "Form E applicability must be tied to the relevant Malaysian LMO contained-use/import-for-contained-use scope and the facts supplied.",
                "BioSafe may explain the likely regulatory pathway and uncertainty but must not make an official legal determination."
            ])

        if _match_any(ql, [
            r"\bdraft\b.{0,80}\bform e\b",
            r"\bform e\b.{0,80}\bdraft\b",
            r"\busing only\b.{0,100}\b(proposal|information|provided|supplied)\b",
        ]):
            matched.append("FORM_E_SOURCE_ONLY")
            modes.append("SOURCE_ONLY_DRAFT")
            constraints.extend([
                "Draft only fields directly supported by supplied material.",
                "Never infer or invent personnel, dates, LMO details, approvals, premises, containment, risk controls or regulatory determinations.",
                "For absent information use the exact placeholder: [Information not provided — confirmation required]."
            ])

        if _match_any(ql, [
            r"\bcompare\b.{0,60}\bform e\b.{0,80}\b(proposal|research)\b",
            r"\bform e\b.{0,80}\b(inconsisten|mismatch|compare)\b",
        ]):
            matched.append("FORM_E_COMPARE_NO_RESOLVE")
            modes.append("COMPARE_NO_SILENT_RESOLUTION")
            constraints.extend([
                "Distinguish true inconsistency from missing information.",
                "Where possible reference the conflicting sections or fields.",
                "Do not silently resolve a discrepancy by choosing one version."
            ])

    # Transport boundary.
    transport_terms = _match_any(ql, [
        r"\btransport\w*\b", r"\bship\w*\b", r"\bshipment\b", r"\bcourier\b",
    ])
    if transport_terms:
        if _match_any(ql, [
            r"\bcan i\b.{0,60}\btransport\b",
            r"\bcan (this|the|my)\b.{0,60}\b(be )?transported\b",
            r"\bmay i\b.{0,60}\btransport\b",
        ]):
            matched.append("TRANSPORT_INFO_REQUIRED")
            modes.append("ASK_BEFORE_TRANSPORT_CONCLUSION")
            constraints.extend([
                "Do not give an unconditional yes/no transport conclusion when classification and shipment context are missing.",
                "Request or identify the need for sample classification/risk, destination, sender/receiver, packaging, transport mode, applicable requirements and carrier constraints."
            ])

        if "air" in ql:
            matched.append("AIR_TRANSPORT_ADDITIONAL")
            modes.append("AIR_TRANSPORT_ADDITIONAL_REQUIREMENTS")
            constraints.extend([
                "Do not assume road-transport requirements are sufficient for air transport.",
                "State that current air-carrier/international transport requirements may add classification, packaging, marking/labelling, documentation, destination/import and carrier-specific constraints."
            ])

    # Authority hierarchy: Malaysian law vs WHO / institutional guidance.
    if (
        "who" in ql
        and _match_any(ql, [
            r"\blegal requirement\b", r"\bmalaysian\b", r"\binstitutional\b", r"\bwhich one\b"
        ])
    ):
        matched.append("AUTHORITY_HIERARCHY")
        modes.append("AUTHORITY_HIERARCHY")
        constraints.extend([
            "Do not present WHO guidance as Malaysian law.",
            "Distinguish Malaysian law/regulation, official Malaysian guidance, institutional procedures and international guidance by authority level.",
            "Escalate unresolved conflicts or ambiguity."
        ])

    # Source currentness.
    if _match_any(ql, [
        r"\bold\b.{0,50}\b(guideline|guidance|document)\b",
        r"\bassume\b.{0,50}\bstill applicable\b",
        r"\bstill current\b",
    ]):
        matched.append("SOURCE_CURRENTNESS")
        modes.append("VERIFY_CURRENTNESS")
        constraints.extend([
            "Do not assume an old online document remains current.",
            "Verify official status, amendment, replacement or supersession and prefer current official sources."
        ])

    # Remove duplicates, preserve order.
    constraints = list(dict.fromkeys(constraints))
    matched = list(dict.fromkeys(matched))
    modes = list(dict.fromkeys(modes))

    return PolicyDecision(
        short_circuit=False,
        mode="+".join(modes) if modes else "STANDARD",
        constraints=constraints,
        reason="Deterministic decision-boundary constraints applied." if matched else "",
        matched_rules=matched,
        deterministic_response=None,
    )


def build_policy_instruction(decision: PolicyDecision) -> str:
    if decision.short_circuit:
        return ""
    if not decision.constraints:
        return "No additional decision-boundary constraints."
    lines = [
        "BIOsafe deterministic policy constraints (higher priority than stylistic preferences):"
    ]
    lines += [f"- {x}" for x in decision.constraints]
    lines += [
        "- If the evidence is insufficient for a conclusion, explicitly state the uncertainty and request the missing information.",
        "- Do not weaken, reinterpret or override these constraints."
    ]
    return "\n".join(lines)
