#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Tuple


KNOWN_RESPONSE_MODE_FIXES = {
    "ask_before_safing": "ask_before_concluding",
    "ask_before_conclusion": "ask_before_concluding",
    "ask_before_conclude": "ask_before_concluding",
}

KNOWN_CLASSIFICATION_FIXES = {
    "ask_before_concluding": "caution",
    "refuse_and_redirect": "refusal",
    "answer": "normal",
}


def normalize_output(obj: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Deterministically repairs only unambiguous structural/schema mistakes.
    Never changes substantive biosafety content.
    """
    if not isinstance(obj, dict):
        return obj, []

    out = deepcopy(obj)
    repairs: List[str] = []

    # Case 1: conclusion accidentally emitted as an object containing the actual
    # textual conclusion in its "reason" field.
    c = out.get("conclusion")
    if isinstance(c, dict):
        reason = c.get("reason")
        if isinstance(reason, str) and reason.strip():
            out["conclusion"] = reason.strip()
            repairs.append("schema:conclusion_object_to_reason_string")

        # If the misplaced object also contains safety fields, use them only when
        # the canonical safety object is absent or incomplete.
        safety = out.get("safety")
        if not isinstance(safety, dict):
            safety = {}
            out["safety"] = safety

        if isinstance(c.get("classification"), str) and not safety.get("classification"):
            safety["classification"] = c["classification"]
            repairs.append("schema:moved_classification_from_conclusion")
        if isinstance(c.get("response_mode"), str) and not safety.get("response_mode"):
            safety["response_mode"] = c["response_mode"]
            repairs.append("schema:moved_response_mode_from_conclusion")
        if isinstance(reason, str) and not safety.get("reason"):
            safety["reason"] = reason
            repairs.append("schema:moved_reason_from_conclusion")

    # Case 2: known near-miss enum spellings.
    safety = out.get("safety")
    if isinstance(safety, dict):
        rm = safety.get("response_mode")
        if isinstance(rm, str) and rm in KNOWN_RESPONSE_MODE_FIXES:
            safety["response_mode"] = KNOWN_RESPONSE_MODE_FIXES[rm]
            repairs.append(f"schema:response_mode:{rm}->{safety['response_mode']}")

        cl = safety.get("classification")
        if isinstance(cl, str) and cl in KNOWN_CLASSIFICATION_FIXES:
            safety["classification"] = KNOWN_CLASSIFICATION_FIXES[cl]
            repairs.append(f"schema:classification:{cl}->{safety['classification']}")

    return out, repairs
