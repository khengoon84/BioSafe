#!/usr/bin/env python3
from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, List, Tuple


def enforce_policy_shell(
    obj: Dict[str, Any],
    policy: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Deterministic post-generation policy enforcement.

    Only rewrites the top-level conclusion when a prohibited authority boundary
    is crossed. Evidence, missing_information, recommendations and limitations
    are preserved unchanged.
    """
    if not isinstance(obj, dict):
        return obj, []

    out = deepcopy(obj)
    repairs: List[str] = []
    rules = set(policy.get("matched_rules") or [])

    c = out.get("conclusion")
    if not isinstance(c, str):
        return out, repairs

    cl = c.lower()

    if "ASSESS_NOT_CERTIFY" in rules:
        prohibited = bool(
            re.search(
                r"\b(project|activity|facility|submission|proposal)\b.{0,30}\bis (biosafety )?(compliant|non-compliant|approved|rejected)\b",
                cl,
            )
            or re.search(r"\bcompliance is confirmed\b|\bofficially compliant\b|\bofficially non-compliant\b", cl)
        )
        if prohibited:
            out["conclusion"] = (
                "I cannot certify compliance or approval. Based on the supplied "
                "information, I can identify apparent alignment and gaps that should "
                "be reviewed by the authorised institutional or regulatory body."
            )
            repairs.append("policy:compliance_conclusion_shell_enforced")

            limitations = out.get("limitations")
            if not isinstance(limitations, list):
                limitations = []
                out["limitations"] = limitations
            boundary_note = (
                "BioSafe provides an advisory assessment and does not make an official "
                "compliance, approval or rejection determination."
            )
            if boundary_note not in limitations:
                limitations.append(boundary_note)

    return out, repairs
