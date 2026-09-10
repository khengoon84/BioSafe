
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Any

@dataclass
class DecisionQualityResult:
    response: dict
    changed: bool
    rule_ids: list[str]
    notes: list[str]

class BioSafeDecisionQualityRefinementV01:
    """
    Stage 9 controlled refinement.

    Scope:
      DQ-MISS-001  Ground missing-information items in scenario/evidence/activated guard.
      DQ-ENTITY-001 Flag uncertain organism/entity names; do not silently correct.
      DQ-NEXT-001  If conclusion says information is insufficient, explicitly tell user
                   what to provide next and why it matters.

    This component does not make regulatory determinations.
    """

    RULE_MISSING = "DQ-MISS-001"
    RULE_ENTITY = "DQ-ENTITY-001"
    RULE_NEXT = "DQ-NEXT-001"

    _insufficient = re.compile(
        r"\b(insufficient|not enough information|cannot determine|unable to determine|"
        r"cannot conclude|not established|unclear whether)\b", re.I
    )

    _organism_like = re.compile(
        r"\b([A-Z][a-z]{2,}\s+[a-z][a-z-]{2,})\b"
    )

    # Deliberately small, high-confidence typo signal. This does NOT auto-correct user input;
    # it only flags apparent uncertainty for confirmation.
    _known_suspect_spellings = {
        "bacillus antracts": "Bacillus anthracis",
        "bacillus anthracis": "Bacillus anthracis",
    }

    _transport_terms = re.compile(
        r"\b(transport|shipping|shipment|courier|send|sending|receive|receiving|"
        r"infectious substance|p620|p650|un3373|category a|category b)\b", re.I
    )
    _facility_terms = re.compile(
        r"\b(facility|laboratory class|lab class|containment level|bsl|biosafety level|"
        r"pc1|pc2|pc3|pc4)\b", re.I
    )
    _lmo_terms = re.compile(
        r"\b(lmo|living modified organism|genetically modified|genetic modification|"
        r"recombinant|modern biotechnology|transgenic|gene[- ]edited)\b", re.I
    )

    def _scenario_text(self, user_query: str, document_text: str, structured_packet: dict | None) -> str:
        return "\n".join(x for x in [
            user_query or "",
            document_text or "",
            str(structured_packet or "")
        ] if x)

    def _activated_rule_ids(self, response: dict) -> set[str]:
        ids = set()
        meta = response.get("_meta") or {}
        app = meta.get("regulatory_applicability_guard") or {}
        ids.update(app.get("rule_ids") or [])
        return ids

    def _ground_missing_items(self, response: dict, scenario: str, activated_ids: set[str]) -> tuple[list[str], list[str]]:
        original = [str(x).strip() for x in (response.get("missing_information") or []) if str(x).strip()]
        kept, removed = [], []

        for item in original:
            low = item.lower()

            # Activated LMO applicability guard explicitly grounds this need.
            if ("living modified" in low or "genet" in low or "recombinant" in low or "modern biotechnology" in low):
                if "RAGUARD-MY-LMO-001" in activated_ids or self._lmo_terms.search(scenario):
                    kept.append(item)
                else:
                    removed.append(item)
                continue

            # Transport details are grounded only when transport is actually in the scenario.
            if "transport" in low or "shipment" in low or "category" in low:
                if self._transport_terms.search(scenario):
                    kept.append(item)
                else:
                    removed.append(item)
                continue

            # Facility class/details are grounded only when facility/containment context appears.
            if "facility" in low or "biosafety level" in low or "containment level" in low or "containment strategy" in low or "lab class" in low or "bsl" in low:
                if self._facility_terms.search(scenario):
                    kept.append(item)
                else:
                    removed.append(item)
                continue

            # Generic hazard/risk classification can be relevant when an organism is actually named.
            if "hazard" in low or "risk classification" in low:
                if self._organism_like.search(scenario):
                    kept.append(item)
                else:
                    removed.append(item)
                continue

            # Preserve items not covered by v0.1 narrow suppression rules.
            kept.append(item)

        return kept, removed

    def _entity_uncertainty(self, user_query: str) -> tuple[bool, str | None, str | None]:
        q = (user_query or "").strip()
        qlow = q.lower()
        for observed, likely in self._known_suspect_spellings.items():
            if observed in qlow:
                # Exact canonical spelling is not uncertain.
                if observed == "bacillus anthracis":
                    return False, None, None
                return True, observed, likely
        return False, None, None

    def _ensure_entity_confirmation(self, response: dict, observed: str, likely: str):
        missing = list(response.get("missing_information") or [])
        item = (
            f"Confirm the organism name. The supplied term '{observed}' may be a misspelling; "
            f"please confirm whether you mean '{likely}' or a different organism."
        )
        if not any("confirm the organism name" in str(x).lower() for x in missing):
            missing.insert(0, item)
        response["missing_information"] = missing[:4]

    def _ensure_actionable_next_step(self, response: dict):
        conclusion = str(response.get("conclusion") or "")
        if not self._insufficient.search(conclusion):
            return False

        missing = [str(x).strip() for x in (response.get("missing_information") or []) if str(x).strip()]
        if not missing:
            missing = [
                "The specific fact or trigger needed to determine whether the regulatory pathway applies."
            ]
            response["missing_information"] = missing

        recs = [str(x).strip() for x in (response.get("recommended_next_step") or []) if str(x).strip()]
        # Make the first recommendation explicitly user-actionable.
        summary = "; ".join(missing[:2])
        actionable = (
            "Please provide or confirm the following before BioSafe concludes applicability: "
            + summary
        )
        if not any("please provide or confirm" in x.lower() for x in recs):
            recs.insert(0, actionable)

        # Add why-it-matters explanation if not already explicit.
        why = (
            "These details are needed because BioSafe should only make a regulatory applicability "
            "conclusion when the relevant trigger facts are established."
        )
        if not any("trigger facts" in x.lower() or "needed because" in x.lower() for x in recs):
            recs.append(why)

        response["recommended_next_step"] = recs[:3]
        return True


    _specific_classification = re.compile(
        r"\b(?:risk\s*group|rg|bsl|biosafety\s*level|class)\s*[-:]?\s*\d+(?:\.\d+)?\b", re.I
    )
    _entity_specific_action = re.compile(
        r"\b(?:isolate|isolation|containment|biocontainment|ppe|biosafety cabinet|"
        r"risk organism|required containment|requires containment)\b", re.I
    )

    def _evidence_text(self, response: dict) -> str:
        return "\n".join(
            str(x.get("statement") or "")
            for x in (response.get("evidence") or [])
            if isinstance(x, dict)
        )

    def _classification_supported(self, text: str, evidence_text: str) -> bool:
        claims = [m.group(0).lower().replace(" ", "") for m in self._specific_classification.finditer(text or "")]
        evidence_norm = (evidence_text or "").lower().replace(" ", "")
        return all(claim in evidence_norm for claim in claims)

    def _enforce_entity_confirmation_dependency(
        self, response: dict, uncertain: bool, likely: str | None
    ) -> bool:
        if not uncertain:
            return False
        conclusion = str(response.get("conclusion") or "")
        recs = [str(x) for x in (response.get("recommended_next_step") or [])]
        combined = " ".join([conclusion] + recs).lower()
        likely_name = (likely or "").lower()
        has_specific_claim = (
            (likely_name and likely_name in combined)
            or bool(self._specific_classification.search(combined))
            or bool(self._entity_specific_action.search(combined))
        )
        if not has_specific_claim:
            return False

        response["conclusion"] = (
            "The organism identity is not yet confirmed, so BioSafe should not make an "
            "organism-specific risk-group, biosafety-level, containment, PPE, transport, "
            "or disposal determination at this stage. Please confirm the organism name first."
        )

        safe_recs = []
        for rec in recs:
            low = rec.lower()
            if (
                "confirm" in low or "clarify" in low or "lmo" in low
                or "genetically modified" in low or "recombinant" in low
                or "modern biotechnology" in low
            ):
                safe_recs.append(rec)
        if not any("confirm the organism" in r.lower() for r in safe_recs):
            safe_recs.insert(0, "Please confirm the organism identity before BioSafe applies organism-specific risk or containment guidance.")
        response["recommended_next_step"] = safe_recs[:3]

        safety = dict(response.get("safety") or {})
        safety["classification"] = "caution"
        safety["response_mode"] = "ask_before_concluding"
        safety["reason"] = "Organism-specific conclusions require the organism identity to be confirmed."
        response["safety"] = safety
        return True

    def _suppress_unsupported_classifications(self, response: dict) -> bool:
        evidence_text = self._evidence_text(response)
        changed = False
        conclusion = str(response.get("conclusion") or "")
        if self._specific_classification.search(conclusion) and not self._classification_supported(conclusion, evidence_text):
            response["conclusion"] = (
                "BioSafe does not have sufficient retrieved evidence to support the specific "
                "risk-group, biosafety-level, or containment classification stated in the draft response."
            )
            changed = True

        new_recs = []
        for rec in (response.get("recommended_next_step") or []):
            text = str(rec)
            if self._specific_classification.search(text) and not self._classification_supported(text, evidence_text):
                changed = True
                continue
            new_recs.append(text)
        response["recommended_next_step"] = new_recs
        return changed


    _my_notification_query = re.compile(
        r"\b(?:malaysia(?:n)?\s+biosafety|biosafety\s+act|biosafety\s+regulations?|"
        r"form\s*e|director\s+general|notify|notification)\b",
        re.I
    )
    _operational_missing = re.compile(
        r"\b(?:containment|biosafety\s*cabinet|bsc|ppe|n95|respirator|full\s+suit|"
        r"gloves?|gown|face\s+shield|risk\s+group|biosafety\s+level|bsl|"
        r"transport\s+category|disposal|decontamination)\b",
        re.I
    )
    _operational_query = re.compile(
        r"\b(?:containment|biosafety\s+cabin(?:et)?|bsc|ppe|n95|respirator|full\s+suit|"
        r"risk\s+group|biosafety\s+level|bsl|transport|ship|courier|disposal|"
        r"decontamination)\b",
        re.I
    )

    def _ensure_malaysia_notification_trigger(self, response: dict, user_query: str) -> bool:
        q = user_query or ""
        if not self._my_notification_query.search(q):
            return False
        if self._lmo_terms.search(q):
            return False

        changed = False
        missing = [str(x).strip() for x in (response.get("missing_information") or []) if str(x).strip()]
        lmo_item = (
            "Whether the organism or activity involves a living modified organism (LMO), "
            "genetic modification, recombinant technology, or another form of modern biotechnology"
        )
        if not any(
            "living modified organism" in x.lower()
            or "genetic modification" in x.lower()
            or "recombinant" in x.lower()
            or "modern biotechnology" in x.lower()
            for x in missing
        ):
            missing.append(lmo_item)
            response["missing_information"] = missing[:4]
            changed = True

        recs = [str(x).strip() for x in (response.get("recommended_next_step") or []) if str(x).strip()]
        rec = (
            "Clarify whether the activity is genetically modified, recombinant, an LMO, "
            "or otherwise within the modern-biotechnology scope before concluding that "
            "the Malaysian Biosafety notification pathway applies."
        )
        if not any("malaysian biosafety notification pathway" in x.lower() for x in recs):
            recs.append(rec)
            response["recommended_next_step"] = recs[:3]
            changed = True

        limitations = [str(x).strip() for x in (response.get("limitations") or []) if str(x).strip()]
        lim = (
            "BioSafe has not made a Malaysian Biosafety notification applicability determination "
            "because the required LMO / modern-biotechnology trigger facts are not established."
        )
        if not any("notification applicability determination" in x.lower() for x in limitations):
            limitations.append(lim)
            response["limitations"] = limitations[:2]
            changed = True

        safety = dict(response.get("safety") or {})
        if safety.get("response_mode") != "ask_before_concluding":
            safety["response_mode"] = "ask_before_concluding"
            changed = True
        safety["classification"] = "caution"
        if not safety.get("reason"):
            safety["reason"] = (
                "A Malaysian Biosafety notification conclusion requires LMO / modern-biotechnology "
                "trigger facts that are not established."
            )
        response["safety"] = safety
        return changed

    def _suppress_entity_dependent_missing(self, response: dict, user_query: str, uncertain: bool) -> bool:
        if not uncertain:
            return False
        if self._operational_query.search(user_query or ""):
            return False

        original = [str(x).strip() for x in (response.get("missing_information") or []) if str(x).strip()]
        kept = []
        changed = False

        for item in original:
            low = item.lower()
            if "confirm the organism" in low:
                kept.append(item)
                continue
            if (
                "living modified organism" in low
                or "genetic modification" in low
                or "recombinant" in low
                or "modern biotechnology" in low
            ):
                kept.append(item)
                continue
            if self._operational_missing.search(item):
                changed = True
                continue
            kept.append(item)

        if changed:
            response["missing_information"] = kept[:4]
        return changed

    def apply(
        self,
        response: dict[str, Any],
        *,
        user_query: str = "",
        document_text: str = "",
        structured_packet: dict | None = None,
    ) -> DecisionQualityResult:
        out = dict(response)
        scenario = self._scenario_text(user_query, document_text, structured_packet)
        activated = self._activated_rule_ids(out)

        changed = False
        rules = []
        notes = []

        kept, removed = self._ground_missing_items(out, scenario, activated)
        if removed:
            out["missing_information"] = kept
            changed = True
            rules.append(self.RULE_MISSING)
            notes.append("Removed ungrounded missing-information items: " + " | ".join(removed))

        uncertain, observed, likely = self._entity_uncertainty(user_query)
        if uncertain and observed and likely:
            self._ensure_entity_confirmation(out, observed, likely)
            changed = True
            rules.append(self.RULE_ENTITY)
            notes.append("Flagged uncertain organism name without silently correcting it.")

        if self._enforce_entity_confirmation_dependency(out, uncertain, likely):
            changed = True
            rules.append("DQ-ENTITY-002")
            notes.append("Withheld organism-specific conclusions pending identity confirmation.")

        if self._suppress_unsupported_classifications(out):
            changed = True
            rules.append("DQ-GROUND-002")
            notes.append("Suppressed explicit classification labels not supported by retrieved evidence.")

        if self._suppress_entity_dependent_missing(out, user_query, uncertain):
            changed = True
            rules.append("DQ-ENTITY-003")
            notes.append("Suppressed downstream organism-specific missing fields pending identity confirmation.")

        if self._ensure_malaysia_notification_trigger(out, user_query):
            changed = True
            rules.append("DQ-REG-001")
            notes.append("Preserved Malaysian Biosafety LMO/modern-biotechnology trigger question.")

        if self._ensure_actionable_next_step(out):
            changed = True
            rules.append(self.RULE_NEXT)
            notes.append("Converted insufficient-information outcome into an explicit user action.")

        if changed:
            meta = dict(out.get("_meta") or {})
            meta["decision_quality_refinement"] = {
                "changed": True,
                "rule_ids": list(dict.fromkeys(rules)),
                "removed_missing_information": removed,
                "entity_uncertainty_flagged": bool(uncertain),
            }
            out["_meta"] = meta

        return DecisionQualityResult(
            out,
            changed,
            list(dict.fromkeys(rules)),
            notes
        )
