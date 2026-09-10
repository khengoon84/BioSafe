"""
Layer-3 concept knowledge: loads the curated concept table and assembles
deterministic educational responses (definition + elaboration + safety note).

Concepts are keyed by the same keys as intent_grammar.CONCEPT_ALIASES:
  biosafety, biosecurity, biosafety_vs_biosecurity, risk_group, bsl, lmo,
  form_e, bwc, pi_ibc

Every answer is general education from the curated table; nothing here asserts
law, permits, approvals, or case-specific conclusions, so fall-through to the
model pipeline remains safe and is the default for unlisted subjects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CONCEPT_PATH = Path(
    "/home/khengoon/biosafe/unified_v1/config/concept_knowledge_v1_0.json"
)


def load_concept_table(path: str | Path = DEFAULT_CONCEPT_PATH) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Concept knowledge table not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if k != "_meta"}


def render_concept_answer(
    concept: str,
    table: Optional[Dict[str, Any]] = None,
    mode: str = "full",
) -> Optional[Dict[str, Any]]:
    """
    Build a deterministic educational answer dict for a concept key.

    mode:
      "full"   - definition + elaboration (default for definitions/differences)
      "elaborate" - elaboration only, framed as additional detail (for follow-ups)

    Returns None when the concept is unknown, so callers can fall through to
    the normal model pipeline.
    """
    t = table if table is not None else load_concept_table()
    entry = t.get(concept)
    if not entry:
        return None
    definition = str(entry.get("definition") or "").strip()
    elaboration = str(entry.get("elaboration") or "").strip()
    examples = str(entry.get("examples") or "").strip()
    safety_note = str(entry.get("safety_note") or "").strip()

    if mode == "elaborate":
        parts = []
        if elaboration:
            parts.append("Here is more detail:\n\n" + elaboration)
        if examples:
            parts.append(examples)
        answer = "\n\n".join(parts) or definition
    else:
        parts = [definition]
        if elaboration:
            parts.append(elaboration)
        answer = "\n\n".join(p for p in parts if p)

    limitations = []
    if safety_note:
        limitations.append(safety_note)

    return {
        "direct_answer": answer,
        "limitations": limitations,
        "applicable_authority": [],
        "evidence": [],
        "missing_information": [],
        "recommended_next_step": [],
        "safety": {
            "classification": "normal",
            "response_mode": "answer",
            "reason": "General educational answer from curated, non-regulatory concept knowledge.",
        },
    }