
from __future__ import annotations
import re
from copy import deepcopy

class RegulatoryLanguageGuardV01:
    VERSION = "0.1"

    INTERNAL_TIER = re.compile(r"\bTier\s*[123](?:\s*\+\s*Tier?\s*[123]|\s*\+\s*[123])?\b", re.I)
    PACKAGING_AS_CATEGORY = re.compile(
        r"\b(?:transport|infectious substance|specimen)\s+categor(?:y|ies)\s*"
        r"(?:\([^)]*\))?\s*(?:is|are|:)?\s*(?:P620|P650)\b", re.I
    )
    VIOLATION = re.compile(
        r"\b(?:violat(?:e|es|ed|ing|ion)|breach(?:es|ed|ing)?|illegal|unlawful|non[- ]compliant)\b",
        re.I
    )
    APPROVAL = re.compile(
        r"\b(?:regulatory|department|government)\s+approval\s+(?:is\s+)?required\b", re.I
    )

    def _rewrite_text(self, text: str, evidence_text: str = "") -> tuple[str, list[str]]:
        original = text
        repairs = []

        if self.INTERNAL_TIER.search(text):
            text = self.INTERNAL_TIER.sub("authoritative evidence", text)
            repairs.append("REG_LANG_INTERNAL_TIER_REMOVED")

        if self.PACKAGING_AS_CATEGORY.search(text):
            text = re.sub(r"\bP620/P650\b", "applicable packaging instruction", text, flags=re.I)
            text = re.sub(r"\bP620\b", "applicable packaging instruction", text, flags=re.I)
            text = re.sub(r"\bP650\b", "applicable packaging instruction", text, flags=re.I)
            repairs.append("REG_LANG_PACKAGING_NOT_CLASSIFICATION")

        # A legal violation conclusion must be explicitly supported by retrieved authoritative evidence.
        if self.VIOLATION.search(text):
            ev = evidence_text.lower()
            explicit_support = any(x in ev for x in [
                "offence", "contravention", "shall not", "prohibited", "violation", "breach"
            ])
            if not explicit_support:
                text = self.VIOLATION.sub("may indicate a regulatory gap requiring verification", text)
                repairs.append("REG_LANG_UNSUPPORTED_VIOLATION_SOFTENED")

        if self.APPROVAL.search(text):
            ev = evidence_text.lower()
            if "approval" not in ev and "require" not in ev:
                text = self.APPROVAL.sub(
                    "the applicable regulatory pathway should be verified", text
                )
                repairs.append("REG_LANG_UNSUPPORTED_APPROVAL_SOFTENED")

        return text, repairs

    def apply(self, response: dict, evidence_bundle: list[dict] | None = None) -> tuple[dict, list[str]]:
        out = deepcopy(response)
        repairs = []
        evidence_text = " ".join(
            str(x.get("text") or x.get("statement") or "") for x in (evidence_bundle or [])
            if x.get("record_type") != "user_document"
        )

        for field in ("conclusion",):
            if isinstance(out.get(field), str):
                out[field], r = self._rewrite_text(out[field], evidence_text)
                repairs += r

        for field in ("missing_information", "recommended_next_step", "limitations"):
            vals = out.get(field)
            if isinstance(vals, list):
                new = []
                for v in vals:
                    if isinstance(v, str):
                        v, r = self._rewrite_text(v, evidence_text)
                        repairs += r
                    new.append(v)
                out[field] = new

        # stable unique repair codes
        repairs = list(dict.fromkeys(repairs))
        return out, repairs
