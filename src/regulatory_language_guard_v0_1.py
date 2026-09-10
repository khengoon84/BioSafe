
from __future__ import annotations
import re
from copy import deepcopy

class RegulatoryLanguageGuardV011:
    VERSION = "0.1.1"

    INTERNAL_TIER = re.compile(r"\bTier\s*[123](?:\s*\+\s*Tier?\s*[123]|\s*\+\s*[123])?\b", re.I)
    VIOLATION = re.compile(
        r"\b(?:violat(?:e|es|ed|ing|ion)|breach(?:es|ed|ing)?|illegal|unlawful|non[- ]compliant|contravene|contravenes|contravened|contravening)\b",
        re.I
    )
    APPROVAL_REQUIRED = re.compile(
        r"\b(?:regulatory|department|government)\s+approval\s+(?:is\s+)?required\b", re.I
    )
    P620P650 = re.compile(r"\bP620\s*/\s*P650\b|\bP620\b|\bP650\b", re.I)

    def _has_explicit_violation_support(self, evidence_text: str) -> bool:
        ev = evidence_text.lower()
        return any(x in ev for x in [
            "offence", "contravention", "shall not", "prohibited",
            "violation", "breach", "penalty"
        ])

    def _has_explicit_approval_support(self, evidence_text: str) -> bool:
        ev = evidence_text.lower()
        return "approval" in ev and any(x in ev for x in ["required", "must", "shall"])

    def _subject_for_softening(self, text: str) -> str:
        # Conservative subject extraction. Stop before legal/compliance predicate verbs.
        m = re.match(
            r"^(The\s+(?:SOP|proposal|form|document|activity|procedure|process|submission|application|record|protocol|study|project))\b",
            text,
            re.I,
        )
        if m:
            return m.group(1)
        return "The activity"

    def _rewrite_clause(self, text: str, evidence_text: str = "") -> tuple[str, list[str]]:
        repairs = []
        out = text.strip()

        if self.INTERNAL_TIER.search(out):
            if re.search(r"\b(?:required|classification|under Malaysian law|compliance)\b", out, re.I):
                out = (
                    "The applicable regulatory requirements should be determined from the "
                    "authoritative Malaysian sources relevant to this activity."
                )
            else:
                out = self.INTERNAL_TIER.sub("the relevant authoritative evidence", out)
            repairs.append("REG_LANG_INTERNAL_TIER_REMOVED")

        if self.P620P650.search(out):
            if re.search(r"\btransport categor(?:y|ies)\b", out, re.I):
                out = (
                    "The infectious-substance classification should be determined before "
                    "selecting the applicable packaging instruction."
                )
            else:
                out = self.P620P650.sub("the applicable packaging instruction", out)
            repairs.append("REG_LANG_PACKAGING_NOT_CLASSIFICATION")

        if self.VIOLATION.search(out) and not self._has_explicit_violation_support(evidence_text):
            subject = self._subject_for_softening(out)
            out = (
                f"{subject} may have a regulatory gap that requires verification against "
                "the applicable Malaysian requirements."
            )
            repairs.append("REG_LANG_UNSUPPORTED_VIOLATION_SOFTENED")

        if self.APPROVAL_REQUIRED.search(out) and not self._has_explicit_approval_support(evidence_text):
            out = (
                "The applicable regulatory pathway should be verified against the relevant "
                "authoritative Malaysian requirements before proceeding."
            )
            repairs.append("REG_LANG_UNSUPPORTED_APPROVAL_SOFTENED")

        return out, list(dict.fromkeys(repairs))

    def apply(self, response: dict, evidence_bundle: list[dict] | None = None) -> tuple[dict, list[str]]:
        out = deepcopy(response)
        repairs = []
        evidence_text = " ".join(
            str(x.get("text") or x.get("statement") or "")
            for x in (evidence_bundle or [])
            if x.get("record_type") != "user_document"
        )

        if isinstance(out.get("conclusion"), str):
            out["conclusion"], r = self._rewrite_clause(out["conclusion"], evidence_text)
            repairs.extend(r)

        for field in ("missing_information", "recommended_next_step", "limitations"):
            vals = out.get(field)
            if isinstance(vals, list):
                new_vals = []
                for v in vals:
                    if isinstance(v, str):
                        v, r = self._rewrite_clause(v, evidence_text)
                        repairs.extend(r)
                    new_vals.append(v)
                out[field] = new_vals

        return out, list(dict.fromkeys(repairs))

RegulatoryLanguageGuardV01 = RegulatoryLanguageGuardV011
