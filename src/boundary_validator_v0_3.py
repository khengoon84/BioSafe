#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List

@dataclass
class BoundaryValidation:
    decision: str
    issues: List[str]
    warnings: List[str]

    def to_dict(self):
        return asdict(self)


def _text(obj: Dict[str, Any]) -> str:
    parts = []
    for k in ("conclusion",):
        if isinstance(obj.get(k), str):
            parts.append(obj[k])
    for k in ("recommended_next_step", "limitations", "missing_information"):
        v = obj.get(k)
        if isinstance(v, list):
            parts.extend(str(x) for x in v if isinstance(x, str))
    return " ".join(parts).lower()


def validate_boundaries(
    parsed_output: Dict[str, Any],
    policy: Dict[str, Any],
) -> BoundaryValidation:
    issues: List[str] = []
    warnings: List[str] = []
    if not isinstance(parsed_output, dict):
        return BoundaryValidation("RETRY", ["boundary:output_not_object"], [])

    t = _text(parsed_output)
    rules = set(policy.get("matched_rules") or [])

    if "PPE_LAYERED_CONTROL" in rules:
        unsafe_ppe = (
            re.search(r"\bppe\b.{0,100}\b(activity|work|laboratory|lab)\b.{0,50}\b(is|considered|can be considered)\b.{0,20}\bsafe\b", t)
            or re.search(r"\bppe\b.{0,50}\b(sufficient|enough)\b", t)
        )
        if unsafe_ppe and not re.search(r"\bppe\b.{0,60}\b(not sufficient|insufficient|not enough|not a standalone|alone does not|alone is not)\b", t):
            issues.append("boundary:ppe_alone_used_as_safety_determination")

    if "SAFETY_DETERMINATION_BOUNDARY" in rules:
        bad = [
            r"\bthe activity is biosafe\b",
            r"\bthe activity is safe\b",
            r"\bthis activity is biosafe\b",
            r"\bthis activity is safe\b",
        ]
        if any(re.search(p, t) for p in bad) and "insufficient information" not in t:
            issues.append("boundary:premature_safety_determination")

    if "ASSESS_NOT_CERTIFY" in rules:
        bad = [
            r"\b(project|activity|facility|submission|proposal)\b.{0,20}\bis compliant\b",
            r"\b(project|activity|facility|submission|proposal)\b.{0,20}\bis not compliant\b",
            r"\b(project|activity|facility|submission|proposal)\b.{0,20}\bis biosafety compliant\b",
            r"\bcompliance is confirmed\b",
            r"\bofficially compliant\b",
            r"\bapproved\b",
        ]
        if any(re.search(p, t) for p in bad):
            issues.append("boundary:ai_certified_compliance_or_approval")

    if "FORM_E_SCOPE_BOUNDARY" in rules:
        if re.search(r"\b(all|every)\b.{0,60}\b(lab|laborator|biological)\b.{0,80}\b(form e|required|must|need)\b", t):
            issues.append("boundary:form_e_overgeneralised_to_all_biological_work")
        if re.search(r"\bform e is mandatory\b.{0,80}\bbiological materials?\b", t):
            issues.append("boundary:form_e_overgeneralised_to_all_biological_work")

    if "FORM_E_SOURCE_ONLY" in rules:
        # We cannot semantically prove fabrication without source-field alignment,
        # so enforce uncertainty language/placeholder when the response admits gaps.
        has_missing = bool(parsed_output.get("missing_information"))
        placeholder = "[information not provided — confirmation required]" in t
        if has_missing and not placeholder:
            warnings.append("boundary:source_only_draft_missing_placeholder")

    if "FORM_E_COMPARE_NO_RESOLVE" in rules:
        if re.search(r"\b(no inconsistenc|fully consistent|no mismatch)\b", t) and not re.search(r"\b(insufficient|cannot determine|not provided|missing)\b", t):
            warnings.append("boundary:comparison_may_overclaim_consistency")

    if "TRANSPORT_INFO_REQUIRED" in rules:
        if re.search(r"^\s*(yes|no)\b", (parsed_output.get("conclusion") or "").lower()):
            issues.append("boundary:unconditional_transport_yes_no")
        if re.search(r"\b(can|may) be transported\b", t) and not re.search(r"\b(insufficient|need|require|classification|destination|packaging|carrier)\b", t):
            issues.append("boundary:transport_conclusion_without_required_context")

    if "AIR_TRANSPORT_ADDITIONAL" in rules:
        bad = [
            r"\broad\b.{0,50}\brequirements\b.{0,40}\b(apply|sufficient|same)\b.{0,30}\bair\b",
            r"\brequirements\b.{0,50}\bapply universally\b",
            r"\bno (additional|different|extra) requirements\b",
        ]
        if any(re.search(p, t) for p in bad):
            issues.append("boundary:air_transport_additional_requirements_denied")

    if "AUTHORITY_HIERARCHY" in rules:
        if re.search(r"\bwho\b.{0,50}\b(malaysian law|statutory requirement|legal requirement in malaysia)\b", t):
            issues.append("boundary:who_guidance_mislabelled_as_malaysian_law")

    if "SOURCE_CURRENTNESS" in rules:
        if re.search(r"\b(still applicable|still current|remains current)\b", t) and not re.search(r"\bverify|check|supersed|replace|amend|official\b", t):
            issues.append("boundary:old_source_assumed_current")

    decision = "RETRY" if issues else ("PASS_WITH_WARNING" if warnings else "PASS")
    return BoundaryValidation(decision, issues, warnings)
