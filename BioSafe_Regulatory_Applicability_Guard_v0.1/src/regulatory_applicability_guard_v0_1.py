
from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass
class ApplicabilityGuardResult:
    response: dict
    changed: bool
    rule_ids: list[str]
    notes: list[str]

class RegulatoryApplicabilityGuardV01:
    RULE_ID = "RAGUARD-MY-LMO-001"

    _lmo_positive = re.compile(
        r"\b(living modified organism|lmo|genetically modified|genetically engineered|"
        r"recombinant\s+(?:dna|organism|microorganism|construct)|genetic modification|"
        r"modern biotechnology|transgenic|gene-edited|gene edited)\b", re.I)

    _lmo_negative = re.compile(
        r"\b(not\s+(?:genetically modified|an lmo|a living modified organism)|"
        r"non[-\s]?lmo|wild[-\s]?type|naturally occurring|unmodified)\b", re.I)

    _mandatory = re.compile(
        r"\b(must\s+(?:notify|submit)|required\s+to\s+(?:notify|submit)|"
        r"requires?\s+(?:prior\s+)?notification|notification\s+is\s+required|"
        r"form\s+e\s+is\s+required|must\s+.*form\s+e|must\s+.*director\s+general)\b", re.I)

    _my_context = re.compile(
        r"\b(biosafety\s+act|act\s*678|biosafety\s+regulations?|form\s+e|"
        r"department\s+of\s+biosafety|director\s+general|contained\s+use)\b", re.I)

    def _status(self, text: str) -> str:
        if self._lmo_negative.search(text or ""):
            return "negative"
        if self._lmo_positive.search(text or ""):
            return "established"
        return "unknown"

    def apply(self, response: dict, *, user_query: str = "", document_text: str = "", structured_packet: dict | None = None):
        out = dict(response)
        scenario = "\n".join([user_query or "", document_text or "", str(structured_packet or "")])
        combined = str(out.get("conclusion") or "") + " " + " ".join(map(str, out.get("recommended_next_step") or []))
        if not self._my_context.search(combined) or not self._mandatory.search(combined):
            return ApplicabilityGuardResult(out, False, [], ["no_applicability_intervention"])

        status = self._status(scenario)
        if status == "established":
            return ApplicabilityGuardResult(out, False, [], ["lmo_trigger_established"])

        out["conclusion"] = (
            "The information supplied is insufficient to determine whether notification under "
            "Malaysia’s Biosafety Act 2007 and Biosafety (Approval and Notification) Regulations 2010 "
            "is required. That pathway depends on whether the activity involves an LMO or modern "
            "biotechnology and on the specific regulated activity."
        )

        missing = list(out.get("missing_information") or [])
        trigger = ("Whether the organism or activity involves a living modified organism (LMO), "
                   "genetic modification, recombinant technology, or another form of modern biotechnology")
        if not any("living modified" in str(x).lower() or "genet" in str(x).lower() for x in missing):
            missing.insert(0, trigger)
        out["missing_information"] = missing[:3]

        out["recommended_next_step"] = [
            "Clarify whether the organism or activity is genetically modified, recombinant, or otherwise falls within the LMO / modern-biotechnology scope before concluding that the Malaysian notification pathway applies.",
            "Assess pathogen-handling, containment, transport, and other applicable requirements separately from the LMO notification question."
        ]

        limits = list(out.get("limitations") or [])
        limits.insert(0, "BioSafe has not made a regulatory applicability determination because the required LMO / modern-biotechnology trigger facts are not established.")
        out["limitations"] = limits[:2]

        safety = dict(out.get("safety") or {})
        safety.update({
            "classification": "caution",
            "response_mode": "ask_before_concluding",
            "reason": "A mandatory Malaysian LMO notification conclusion requires trigger facts that are not established in the supplied information."
        })
        out["safety"] = safety

        meta = dict(out.get("_meta") or {})
        meta["regulatory_applicability_guard"] = {
            "changed": True, "rule_ids": [self.RULE_ID], "trigger_status": status
        }
        out["_meta"] = meta

        return ApplicabilityGuardResult(
            out, True, [self.RULE_ID],
            ["unsupported mandatory applicability conclusion softened"]
        )
