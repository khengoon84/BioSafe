
from __future__ import annotations
import re
from policy_decision_guard_v0_3_2 import classify_policy as _base_classify_policy, build_policy_instruction as _base_build_policy_instruction

_CERT_PATTERNS = [
    re.compile(r"\bcan\s+(?:biosafe|you)\s+(?:officially\s+)?(?:approve|certify)\b", re.I),
    re.compile(r"\b(?:approve|certify)\s+(?:that\s+)?(?:my|this|the)\b", re.I),
    re.compile(r"\b(?:does|do|is|are)\b.{0,50}\b(?:comply|compliant|compliance)\b", re.I),
    re.compile(r"\b(?:can|could)\s+you\b.{0,50}\b(?:confirm|determine)\b.{0,40}\b(?:compliance|compliant|complies)\b", re.I),
    re.compile(r"\b(?:official|formal|regulatory)\b.{0,40}\b(?:approval|certification|compliance determination)\b", re.I),
]

def _clone_policy(base):
    # Reuse the installed PolicyDecision type without assuming dataclass semantics.
    cls = type(base)
    try:
        return cls(
            short_circuit=False,
            mode="ASSESS_NOT_CERTIFY",
            constraints=[],
            reason="Deterministic decision-boundary constraints applied.",
            matched_rules=["ASSESS_NOT_CERTIFY_COMPLIANCE_BOUNDARY"],
            deterministic_response=None,
        )
    except TypeError:
        try:
            obj = cls(False, "ASSESS_NOT_CERTIFY", [], "Deterministic decision-boundary constraints applied.",
                      ["ASSESS_NOT_CERTIFY_COMPLIANCE_BOUNDARY"], None)
            return obj
        except Exception:
            # Last-resort mutation of base-shaped object.
            base.short_circuit = False
            base.mode = "ASSESS_NOT_CERTIFY"
            base.constraints = []
            base.reason = "Deterministic decision-boundary constraints applied."
            base.matched_rules = ["ASSESS_NOT_CERTIFY_COMPLIANCE_BOUNDARY"]
            base.deterministic_response = None
            return base

def _constraints():
    return [
        "BioSafe is an advisory system and must not certify, approve, or make an official regulatory compliance determination.",
        "Do not conclude that an activity, facility, SOP, proposal, or arrangement 'complies', 'is compliant', 'does not comply', 'is non-compliant', or equivalent unless an authoritative determination is explicitly supplied by the user.",
        "When facts are incomplete, identify the evidence, gaps, likely regulatory pathway, uncertainty, and next steps instead of issuing a positive or negative compliance verdict.",
        "PROHIBITED conclusions include: 'Your activity complies', 'Your activity does not comply', 'Your arrangements are compliant', 'Your arrangements are not compliant', 'BioSafe approves this', 'BioSafe certifies this'.",
        "ALLOWED framing: 'BioSafe cannot certify or approve compliance. Based on the supplied information, the following requirements, gaps, and uncertainties should be reviewed against the applicable authority.'",
    ]

def classify_policy(query: str):
    base = _base_classify_policy(query)

    # Preserve stronger existing modes/short-circuits first.
    if getattr(base, "short_circuit", False):
        return base
    mode = getattr(base, "mode", "STANDARD")
    if mode not in ("STANDARD", "", None):
        return base

    q = query or ""
    if any(p.search(q) for p in _CERT_PATTERNS):
        obj = _clone_policy(base)
        obj.constraints = _constraints()
        return obj

    return base

def build_policy_instruction(decision):
    if getattr(decision, "mode", "") == "ASSESS_NOT_CERTIFY":
        constraints = getattr(decision, "constraints", []) or _constraints()
        return (
            "POLICY MODE: ASSESS_NOT_CERTIFY\n"
            + "\n".join(f"- {c}" for c in constraints)
        )
    return _base_build_policy_instruction(decision)
