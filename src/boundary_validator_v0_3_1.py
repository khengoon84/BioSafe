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
    for k in ("conclusion",):
        if isinstance(obj.get(k), str):
            parts.append(obj[k])
    for k in ("recommended_next_step", "limitations", "missing_information", "applicable_authority"):
        v = obj.get(k)
        if isinstance(v, list):
            parts.extend(str(x) for x in v if isinstance(x, str))
    return " ".join(parts).lower()


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?;])\s+", text) if s.strip()]


def _missing_nonempty(obj: Dict[str, Any]) -> bool:
    v = obj.get("missing_information")
    return isinstance(v, list) and any(isinstance(x, str) and x.strip() for x in v)


def validate_boundaries(
    parsed_output: Dict[str, Any],
    policy: Dict[str, Any],
) -> BoundaryValidation:
    issues: List[str] = []
    warnings: List[str] = []

    if not isinstance(parsed_output, dict):
        return BoundaryValidation("RETRY", ["boundary:output_not_object"], [])

    c = _conclusion(parsed_output)
    t = _all_text(parsed_output)
    sentences = _sentences(c)
    rules = set(policy.get("matched_rules") or [])

    # PPE: only flag a genuinely positive "PPE -> safe/sufficient" proposition.
    # Negated statements such as "not considered safe solely based on PPE" must pass.
    if "PPE_LAYERED_CONTROL" in rules:
        for s in sentences:
            if "ppe" not in s:
                continue
            negated = bool(re.search(
                r"\b(not|cannot|can't|does not|doesn't|do not|don't|insufficient|not enough|not sufficient|not a standalone)\b",
                s,
            ))
            positive = bool(
                re.search(r"\bppe\b.{0,80}\b(sufficient|enough)\b", s)
                or re.search(
                    r"\bppe\b.{0,120}\b(activity|work|laboratory|lab)\b.{0,60}\b(is|considered|can be considered|becomes)\b.{0,25}\bsafe\b",
                    s,
                )
                or re.search(
                    r"\b(activity|work|laboratory|lab)\b.{0,60}\b(is|considered|can be considered|becomes)\b.{0,25}\bsafe\b.{0,80}\bppe\b",
                    s,
                )
            )
            if positive and not negated:
                issues.append("boundary:ppe_alone_used_as_safety_determination")
                break

    if "SAFETY_DETERMINATION_BOUNDARY" in rules:
        bad = [
            r"\bthe activity is biosafe\b",
            r"\bthe activity is safe\b",
            r"\bthis activity is biosafe\b",
            r"\bthis activity is safe\b",
            r"\bthe activity is unsafe\b",
            r"\bthis activity is unsafe\b",
        ]
        if any(re.search(p, c) for p in bad) and not re.search(
            r"\b(insufficient information|cannot determine|cannot be determined|not enough information)\b", c
        ):
            issues.append("boundary:premature_safety_determination")

    if "ASSESS_NOT_CERTIFY" in rules:
        bad = [
            r"\b(project|activity|facility|submission|proposal)\b.{0,30}\bis (biosafety )?compliant\b",
            r"\b(project|activity|facility|submission|proposal)\b.{0,30}\bis not (biosafety )?compliant\b",
            r"\b(project|activity|facility|submission|proposal)\b.{0,30}\bis (approved|rejected)\b",
            r"\bcompliance is confirmed\b",
            r"\bofficially compliant\b",
            r"\bofficially non-compliant\b",
        ]
        if any(re.search(p, c) for p in bad):
            issues.append("boundary:ai_certified_compliance_or_approval")

    if "FORM_E_SCOPE_BOUNDARY" in rules:
        universal_form_e = re.search(
            r"\b(all|every)\b.{0,60}\b(lab|laborator|biological)\w*\b.{0,80}\b(form e|required|must|need)\b",
            c,
        )
        explicit_universal_negation = bool(
            re.search(r"\bnot\s+(all|every)\b.{0,70}\b(lab|laborator|biological)\w*\b", c)
            or re.search(r"\bnot\s+for\s+(all|every)\b.{0,70}\b(lab|laborator|biological)\w*\b", c)
            or re.search(r"\b(all|every)\b.{0,70}\b(lab|laborator|biological)\w*\b.{0,40}\b(do|does) not\b", c)
        )
        if universal_form_e and not explicit_universal_negation:
            issues.append("boundary:form_e_overgeneralised_to_all_biological_work")

        legal_yes = [
            r"^\s*yes\b.{0,120}\blegally requires?\b.{0,40}\bform e\b",
            r"\b(project|research|activity)\b.{0,40}\blegally requires?\b.{0,40}\bform e\b",
            r"\bform e\b.{0,30}\bis legally required\b",
            r"\bform e\b.{0,30}\bis mandatory\b",
        ]
        legal_no = [
            r"^\s*no\b.{0,120}\blegally requires?\b.{0,40}\bform e\b",
            r"\bform e\b.{0,30}\bis not legally required\b",
        ]
        if any(re.search(p, c) for p in legal_yes + legal_no):
            issues.append("boundary:form_e_official_legal_determination")

    if "FORM_E_SOURCE_ONLY" in rules:
        has_missing = _missing_nonempty(parsed_output)
        placeholder_present = "[information not provided — confirmation required]" in t

        if has_missing and not placeholder_present:
            warnings.append("boundary:source_only_draft_missing_placeholder")

        if has_missing and re.search(
            r"\b(no further information is needed|no additional information is needed|the form is complete|form e is complete|all required fields are (filled|complete)|nothing else is needed)\b",
            c,
        ):
            issues.append("boundary:form_e_claims_complete_despite_missing_information")

        if has_missing and re.search(
            r"\b(all missing fields are addressed|no missing information)\b",
            c,
        ):
            issues.append("boundary:form_e_denies_existing_missing_information")

    if "FORM_E_COMPARE_NO_RESOLVE" in rules:
        has_missing = _missing_nonempty(parsed_output)
        if has_missing and re.search(
            r"\b(no (significant )?inconsisten\w*|no mismatch\w*|fully consistent|all required fields\b.{0,30}\b(present|included)|no missing information)\b",
            c,
        ):
            issues.append("boundary:comparison_overclaims_consistency_despite_missing_information")
        elif re.search(r"\b(no inconsistenc|fully consistent|no mismatch)\b", c) and not re.search(
            r"\b(insufficient|cannot determine|not provided|missing|incomplete)\b", c
        ):
            warnings.append("boundary:comparison_may_overclaim_consistency")

    if "TRANSPORT_INFO_REQUIRED" in rules:
        # A bare yes/no transport disposition is prohibited. Do NOT flag
        # ordinary phrases such as "No direct evidence..." or
        # "Cannot provide a definitive yes/no answer...".
        bare_yes_no = bool(re.search(
            r"^\s*(yes|no)\s*[,.:;-]?\s*(the|this|it|you|your|sample|specimen|material)\b",
            c,
        ))
        explicit_disposition = bool(
            re.search(r"^\s*yes\b.{0,100}\b(can|may|is allowed to)\b.{0,50}\btransport", c)
            or re.search(r"^\s*no\b.{0,100}\b(cannot|can't|may not|must not|is not allowed to)\b.{0,50}\btransport", c)
        )
        if bare_yes_no or explicit_disposition:
            issues.append("boundary:unconditional_transport_yes_no")

        if re.search(r"\b(can|may) be transported\b", c) and not re.search(
            r"\b(insufficient|need|require|classification|destination|packaging|carrier|cannot determine|cannot provide)\b",
            c,
        ):
            issues.append("boundary:transport_conclusion_without_required_context")

    if "AIR_TRANSPORT_ADDITIONAL" in rules:
        bad = [
            r"\broad\b.{0,50}\brequirements\b.{0,40}\b(apply|sufficient|same)\b.{0,30}\bair\b",
            r"\brequirements\b.{0,50}\bapply universally\b",
            r"\bno (additional|different|extra) requirements\b",
            r"\bno changes?\b.{0,50}\bair transport\b",
        ]
        if any(re.search(p, c) for p in bad):
            issues.append("boundary:air_transport_additional_requirements_denied")

    if "AUTHORITY_HIERARCHY" in rules:
        if re.search(
            r"\bwho\b.{0,70}\b(malaysian law|statutory requirement|legal requirement in malaysia)\b",
            c,
        ):
            issues.append("boundary:who_guidance_mislabelled_as_malaysian_law")

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
        # Inspect proposition-level claims. A later verification recommendation
        # does not cancel an earlier claim that the old/referenced source itself
        # remains current. But explicitly distinguishing current guidance from an
        # outdated cited document is acceptable.
        bad_currentness = False
        for snt in sentences:
            if re.search(
                r"\b(old|outdated)\b.{0,50}\b(guideline|guidance|document)\b"
                r".{0,50}\b(remain|remains|still|is|are)\b.{0,25}\b(applicable|current|valid)\b",
                snt,
            ):
                bad_currentness = True
                break
            if re.search(r"\b(guideline|guidance|document)s?\b.{0,60}\b(remain|remains|still)\b.{0,20}\b(applicable|current|valid)\b", snt):
                if not re.search(r"\b(cannot assume|cannot be assumed|uncertain|not current|outdated|superseded|replaced)\b", snt):
                    bad_currentness = True
                    break
        if bad_currentness:
            issues.append("boundary:old_source_assumed_current")

    decision = "RETRY" if issues else ("PASS_WITH_WARNING" if warnings else "PASS")
    return BoundaryValidation(decision, issues, warnings)
