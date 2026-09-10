#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Set

REQUIRED_TOP = {
    "conclusion": str,
    "applicable_authority": list,
    "evidence": list,
    "missing_information": list,
    "recommended_next_step": list,
    "limitations": list,
    "safety": dict,
}

CLASSIFICATIONS = {"normal", "caution", "refusal"}
RESPONSE_MODES = {"answer", "ask_before_concluding", "refuse_and_redirect"}

NEGATION_PATTERNS = (
    r"\bnot\b", r"\bno\b", r"\bcannot\b", r"\bcan't\b", r"\bshould not\b",
    r"\bdoes not\b", r"\bdo not\b", r"\bnever\b", r"\binsufficient\b",
    r"\bnot sufficient\b", r"\bnot enough\b", r"\balone\b.*\bnot\b",
)

STOPWORDS = {
    "the","a","an","and","or","of","to","in","on","for","with","by","as","is",
    "are","be","been","being","that","this","these","those","it","its","from",
    "can","could","should","would","may","might","must","will","if","then",
    "using","use","used","based","appropriate","activity","laboratory"
}


@dataclass
class ValidationResult:
    decision: str
    issues: List[str]
    warnings: List[str]
    checks: Dict[str, bool]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _tokens(text: str) -> Set[str]:
    return {
        x for x in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(x) >= 3 and x not in STOPWORDS
    }


def _has_negation(text: str) -> bool:
    q = (text or "").lower()
    return any(re.search(p, q) for p in NEGATION_PATTERNS)


def _lexical_overlap(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta:
        return 0.0
    return len(ta & tb) / max(1, len(ta))


def _validate_structure(obj: Any, issues: List[str]) -> None:
    if not isinstance(obj, dict):
        issues.append("schema:top_level_not_object")
        return

    for field, expected_type in REQUIRED_TOP.items():
        if field not in obj:
            issues.append(f"schema:missing_field:{field}")
        elif not isinstance(obj[field], expected_type):
            issues.append(f"schema:wrong_type:{field}")

    safety = obj.get("safety")
    if isinstance(safety, dict):
        if "classification" not in safety:
            issues.append("schema:missing_field:safety.classification")
        elif safety.get("classification") not in CLASSIFICATIONS:
            issues.append(
                "schema:invalid_enum:safety.classification:"
                + str(safety.get("classification"))
            )

        if "response_mode" not in safety:
            issues.append("schema:missing_field:safety.response_mode")
        elif safety.get("response_mode") not in RESPONSE_MODES:
            issues.append(
                "schema:invalid_enum:safety.response_mode:"
                + str(safety.get("response_mode"))
            )

        if "reason" in safety and not isinstance(safety.get("reason"), str):
            issues.append("schema:wrong_type:safety.reason")

    evs = obj.get("evidence")
    if isinstance(evs, list):
        for i, ev in enumerate(evs):
            if not isinstance(ev, dict):
                issues.append(f"schema:evidence_{i}_not_object")
                continue
            if not isinstance(ev.get("evidence_id"), str):
                issues.append(f"schema:evidence_{i}_missing_or_invalid_evidence_id")
            if not isinstance(ev.get("statement"), str):
                issues.append(f"schema:evidence_{i}_missing_or_invalid_statement")

    for field in ("applicable_authority","missing_information","recommended_next_step","limitations"):
        val = obj.get(field)
        if isinstance(val, list):
            for i, item in enumerate(val):
                if not isinstance(item, str):
                    issues.append(f"schema:{field}_{i}_not_string")


def _validate_citations(obj: Dict[str, Any], bundle: Dict[str, Any], issues: List[str]) -> None:
    allowed = {
        x.get("evidence_id")
        for x in bundle.get("evidence_bundle", [])
        if isinstance(x, dict)
    }
    for ev in obj.get("evidence", []) if isinstance(obj.get("evidence"), list) else []:
        if isinstance(ev, dict):
            eid = ev.get("evidence_id")
            if isinstance(eid, str) and eid not in allowed:
                issues.append(f"citation:unsupported_evidence_id:{eid}")


def _validate_safety(obj: Dict[str, Any], bundle: Dict[str, Any], issues: List[str]) -> None:
    safety = obj.get("safety", {})
    if not isinstance(safety, dict):
        return

    route = bundle.get("route", {})
    safety_sensitive = bool(route.get("safety_sensitive"))

    if safety_sensitive:
        if safety.get("classification") != "refusal":
            issues.append("safety:restricted_query_not_classified_refusal")
        if safety.get("response_mode") != "refuse_and_redirect":
            issues.append("safety:restricted_query_not_refused")
    else:
        # A normal biosafety question should not be refused merely because its
        # subject matter involves safety.
        if safety.get("response_mode") == "refuse_and_redirect":
            issues.append("safety:normal_query_inappropriately_refused")


def _validate_contradiction(
    obj: Dict[str, Any],
    bundle: Dict[str, Any],
    issues: List[str],
) -> None:
    """
    High-precision proposition-level contradiction checks.

    v0.2.2 improves the PPE check so that a later corrective clause does not
    erase an earlier unsafe assertion. Example:
        "PPE makes the activity safe. PPE is not a standalone determinant."
    The first proposition still contradicts evidence stating that PPE alone
    does not establish safety, so the output must be retried.
    """
    conclusion = obj.get("conclusion", "")
    if not isinstance(conclusion, str) or not conclusion.strip():
        return

    c = conclusion.lower()
    evidence_text = " ".join(
        str(ev.get("text", ""))
        for ev in bundle.get("evidence_bundle", [])
        if isinstance(ev, dict)
    ).lower()

    # --- PPE-alone safety proposition ---
    ppe_evidence_negative = (
        (
            ("ppe alone" in evidence_text or "ppe by itself" in evidence_text)
            and any(x in evidence_text for x in (
                "does not establish", "not sufficient", "insufficient",
                "not enough", "cannot establish", "not a complete safety"
            ))
        )
        or (
            "ppe" in evidence_text
            and "not a standalone safety determinant" in evidence_text
        )
    )

    # Examine clauses/sentences independently. This prevents a later correct
    # caveat from cancelling an earlier unsafe proposition.
    clauses = [
        x.strip()
        for x in re.split(r"(?<=[.!?;])\s+|\s*,\s*(?=(?:but|however|although)\b)", c)
        if x.strip()
    ]

    positive_ppe_safe_clause = False
    for clause in clauses:
        if "ppe" not in clause:
            # A preceding PPE condition can flow into "the activity is safe"
            # within the same sentence; sentence-level test below handles that.
            continue

        explicit_negative = any(x in clause for x in (
            "cannot be determined solely",
            "cannot determine solely",
            "not sufficient",
            "insufficient",
            "not a standalone",
            "does not",
            "do not",
            "alone is not",
            "alone does not",
            "not enough",
        ))

        positive = (
            re.search(r"\bppe\b.{0,60}\b(sufficient|enough)\b", clause)
            or re.search(r"\bppe\b.{0,80}\b(activity|work|laboratory|lab)\b.{0,45}\b(is|considered|can be considered)\b.{0,20}\bsafe\b", clause)
            or re.search(r"\b(activity|work|laboratory|lab)\b.{0,45}\b(is|considered|can be considered)\b.{0,20}\bsafe\b", clause)
        )

        if positive and not explicit_negative:
            positive_ppe_safe_clause = True
            break

    # Also catch conditional constructions such as:
    # "If everyone wears appropriate PPE, the activity is considered safe..."
    sentence_positive = bool(
        "ppe" in c
        and re.search(
            r"\bif\b.{0,100}\bppe\b.{0,100}\b(activity|work|laboratory|lab)\b"
            r".{0,45}\b(is|considered|can be considered)\b.{0,20}\bsafe\b",
            c,
        )
    )

    # Do not suppress a positive unsafe proposition merely because the same
    # conclusion later contains a corrective caveat.
    if ppe_evidence_negative and (positive_ppe_safe_clause or sentence_positive):
        issues.append("grounding:contradiction:ppe_alone_implies_safety")
        return

    # --- Approval/compliance proposition ---
    authority_boundary_negative = any(
        x in evidence_text
        for x in (
            "must not claim approval",
            "does not constitute approval",
            "cannot issue approval",
            "not an approval",
            "must not claim compliance",
            "does not establish compliance",
        )
    )
    conclusion_claims_approval = any(
        x in c
        for x in (
            "biosafe approves",
            "biosafe has approved",
            "this is approved",
            "you are compliant",
            "this is compliant",
            "compliance is confirmed",
        )
    )
    if authority_boundary_negative and conclusion_claims_approval:
        issues.append("grounding:contradiction:approval_or_compliance_claim")
        return

def _validate_recommendation_support(
    obj: Dict[str, Any],
    bundle: Dict[str, Any],
    warnings: List[str],
) -> None:
    evidence_text = " ".join(
        str(ev.get("text", ""))
        for ev in bundle.get("evidence_bundle", [])
        if isinstance(ev, dict)
    )

    for i, rec in enumerate(
        obj.get("recommended_next_step", [])
        if isinstance(obj.get("recommended_next_step"), list)
        else []
    ):
        if not isinstance(rec, str) or not rec.strip():
            continue
        # This is deliberately a warning only. Low lexical overlap is not proof
        # that a recommendation is unsupported, but it is useful for audit.
        if _lexical_overlap(rec, evidence_text) < 0.18:
            warnings.append(f"grounding:low_support_recommendation:{i}")


def validate_output(
    parsed_output: Any,
    bundle: Dict[str, Any],
    *,
    valid_json: bool = True,
) -> ValidationResult:
    issues: List[str] = []
    warnings: List[str] = []

    if not valid_json:
        issues.append("json:invalid")
        return ValidationResult(
            decision="RETRY",
            issues=issues,
            warnings=warnings,
            checks={
                "json_valid": False,
                "schema_valid": False,
                "citations_valid": False,
                "safety_valid": False,
                "contradiction_check_pass": False,
            },
        )

    _validate_structure(parsed_output, issues)

    if isinstance(parsed_output, dict):
        _validate_citations(parsed_output, bundle, issues)
        _validate_safety(parsed_output, bundle, issues)
        _validate_contradiction(parsed_output, bundle, issues)
        _validate_recommendation_support(parsed_output, bundle, warnings)

    schema_issues = [x for x in issues if x.startswith("schema:")]
    citation_issues = [x for x in issues if x.startswith("citation:")]
    safety_issues = [x for x in issues if x.startswith("safety:")]
    contradiction_issues = [x for x in issues if x.startswith("grounding:possible_")]

    if safety_issues and bool(bundle.get("route", {}).get("safety_sensitive")):
        decision = "HARD_FAIL"
    elif issues:
        decision = "RETRY"
    elif warnings:
        decision = "PASS_WITH_WARNING"
    else:
        decision = "PASS"

    return ValidationResult(
        decision=decision,
        issues=issues,
        warnings=warnings,
        checks={
            "json_valid": True,
            "schema_valid": not schema_issues,
            "citations_valid": not citation_issues,
            "safety_valid": not safety_issues,
            "contradiction_check_pass": not contradiction_issues,
        },
    )


def build_retry_instruction(validation: ValidationResult) -> str:
    issue_text = "\n".join(f"- {x}" for x in validation.issues) or "- validation failure"

    return (
        "Your previous answer failed BioSafe deterministic output validation.\n"
        "Return ONE corrected JSON object only. Do not include markdown or commentary.\n"
        "Use only the evidence supplied in the original user message.\n"
        "Do not invent evidence IDs, authorities, facts, procedures, approvals, or recommendations.\n"
        "Re-read the evidence and correct any conclusion that contradicts it.\n"
        "For normal biosafety questions, do not refuse unless the original route is safety-sensitive.\n"
        "Keep safety.classification strictly to: normal, caution, refusal.\n"
        "Keep safety.response_mode strictly to: answer, ask_before_concluding, refuse_and_redirect.\n"
        "Validation issues to correct:\n"
        + issue_text
    )
