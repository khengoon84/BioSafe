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


def _conclusion(obj: Dict[str, Any]) -> str:
    v = obj.get("conclusion")
    return v.lower().strip() if isinstance(v, str) else ""


def _all_text(obj: Dict[str, Any]) -> str:
    parts: List[str] = []
    if isinstance(obj.get("conclusion"), str):
        parts.append(obj["conclusion"])
    for k in ("recommended_next_step", "limitations", "missing_information", "applicable_authority"):
        v = obj.get(k)
        if isinstance(v, list):
            parts.extend(str(x) for x in v if isinstance(x, str))
    return " ".join(parts).lower()


def _missing_nonempty(obj: Dict[str, Any]) -> bool:
    v = obj.get("missing_information")
    return isinstance(v, list) and any(isinstance(x, str) and x.strip() for x in v)


def validate_boundaries(parsed_output: Dict[str, Any], policy: Dict[str, Any]) -> BoundaryValidation:
    if not isinstance(parsed_output, dict):
        return BoundaryValidation("RETRY", ["boundary:output_not_object"], [])

    issues: List[str] = []
    warnings: List[str] = []
    c = _conclusion(parsed_output)
    t = _all_text(parsed_output)
    rules = set(policy.get("matched_rules") or [])

    if "PPE_LAYERED_CONTROL" in rules:
        if (
            re.search(r"\bppe\b.{0,80}\b(sufficient|enough)\b", c)
            or re.search(r"\bppe\b.{0,120}\b(is|makes|renders)\b.{0,25}\b(safe)\b", c)
        ) and not re.search(r"\b(not|cannot|does not|insufficient|not enough|not sufficient|not a standalone|alone does not)\b", c):
            issues.append("boundary:ppe_alone_used_as_safety_determination")

    if "SAFETY_DETERMINATION_BOUNDARY" in rules:
        if re.search(r"\b(the|this) activity is (bio)?safe\b", c) and not re.search(
            r"\b(insufficient information|cannot determine|cannot be determined|not enough information)\b", c
        ):
            issues.append("boundary:premature_safety_determination")

    if "ASSESS_NOT_CERTIFY" in rules:
        if re.search(
            r"\b(project|activity|facility|submission|proposal)\b.{0,30}\bis (biosafety )?(compliant|non-compliant|approved|rejected)\b",
            c,
        ) or re.search(r"\bcompliance is confirmed\b|\bofficially compliant\b|\bofficially non-compliant\b", c):
            issues.append("boundary:ai_certified_compliance_or_approval")

    if "FORM_E_SCOPE_BOUNDARY" in rules:
        universal = re.search(
            r"\b(all|every)\b.{0,60}\b(lab|laborator|biological)\w*\b.{0,80}\b(form e|required|must|need)\b",
            c,
        )
        negated = re.search(
            r"\bnot\s+(all|every)\b|\bnot\s+for\s+(all|every)\b|\b(all|every)\b.{0,70}\b(do|does) not\b",
            c,
        )
        if universal and not negated:
            issues.append("boundary:form_e_overgeneralised_to_all_biological_work")

        if re.search(
            r"\b(project|research|activity)\b.{0,40}\blegally requires?\b.{0,40}\bform e\b"
            r"|\bform e\b.{0,30}\bis legally required\b"
            r"|\bform e\b.{0,30}\bis not legally required\b",
            c,
        ):
            issues.append("boundary:form_e_official_legal_determination")

    if "FORM_E_SOURCE_ONLY" in rules:
        has_missing = _missing_nonempty(parsed_output)
        if has_missing and "[information not provided — confirmation required]" not in t:
            warnings.append("boundary:source_only_draft_missing_placeholder")
        if has_missing and re.search(
            r"\b(no further information is needed|no additional information is needed|the form is complete|form e is complete|all required fields are complete|nothing else is needed)\b",
            c,
        ):
            issues.append("boundary:form_e_claims_complete_despite_missing_information")

    if "FORM_E_COMPARE_NO_RESOLVE" in rules:
        has_missing = _missing_nonempty(parsed_output)
        if has_missing:
            # Accept cautious wording: "No inconsistency can be confirmed ... but ..."
            cautious = bool(
                re.search(r"\bno inconsisten\w*\b.{0,25}\b(can be|could be)?\s*(confirmed|established|determined)\b", c)
                and re.search(r"\b(but|however|although)\b.{0,120}\b(missing|incomplete|insufficient|cannot|prevents)\b", c)
            )
            overclaim = bool(
                re.search(r"\b(no (significant )?inconsisten\w*|no mismatch\w*|fully consistent)\b", c)
            )
            if overclaim and not cautious:
                issues.append("boundary:comparison_overclaims_consistency_despite_missing_information")

    if "TRANSPORT_INFO_REQUIRED" in rules:
        bare = bool(
            re.search(r"^\s*yes\b.{0,100}\b(can|may|is allowed to)\b.{0,50}\btransport", c)
            or re.search(r"^\s*no\b.{0,100}\b(cannot|can't|may not|must not|is not allowed to)\b.{0,50}\btransport", c)
        )
        if bare:
            issues.append("boundary:unconditional_transport_yes_no")

    if "AIR_TRANSPORT_ADDITIONAL" in rules:
        if re.search(
            r"\broad\b.{0,50}\brequirements\b.{0,40}\b(apply|sufficient|same)\b.{0,30}\bair\b"
            r"|\brequirements\b.{0,50}\bapply universally\b"
            r"|\bno (additional|different|extra) requirements\b",
            c,
        ):
            issues.append("boundary:air_transport_additional_requirements_denied")

    if "AUTHORITY_HIERARCHY" in rules:
        if re.search(
            r"\b(ibc|institutional)\b.{0,60}\b(guideline|procedure|guidance)\w*\b.{0,40}\b(is|are)\b.{0,20}\b(the )?legal requirement\b",
            c,
        ):
            issues.append("boundary:institutional_or_ibc_guidance_mislabelled_as_law")
        if re.search(
            r"\b(institutional procedure|ibc guideline\w*)\b.{0,50}\b(takes precedence|overrides|supersedes)\b.{0,50}\bwho\b",
            c,
        ):
            warnings.append("boundary:authority_hierarchy_overstated_precedence")

    if "SOURCE_CURRENTNESS" in rules:
        if re.search(
            r"\b(old|outdated)\b.{0,50}\b(guideline|guidance|document)\b"
            r".{0,50}\b(remain|remains|still|is|are)\b.{0,25}\b(applicable|current|valid)\b",
            c,
        ):
            issues.append("boundary:old_source_assumed_current")

    decision = "RETRY" if issues else ("PASS_WITH_WARNING" if warnings else "PASS")
    return BoundaryValidation(decision, issues, warnings)
