
from __future__ import annotations
import re
from typing import Any

def enforce_retrieved_claim_semantic_consistency(
    output: dict[str, Any],
    evidence_bundle: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """
    Narrow regression guard for CLM-028 semantic inversion.

    CLM-028 says the MOH clinical-specimen transport guideline does NOT serve
    as the clinical-waste guideline; clinical waste/chemical waste are outside
    its scope. The model must not invert this into a claim that clinical-
    specimen transport itself is outside the guideline's scope.
    """
    if not isinstance(output, dict):
        return output, []

    has_clm028 = any(ev.get("evidence_id") == "CLM-028" for ev in (evidence_bundle or []))
    if not has_clm028:
        return output, []

    repaired = dict(output)
    changes = []

    bad_patterns = [
        r"clinical[- ]specimen transport.*outside (?:its|the) scope",
        r"exclude[s]? clinical[- ]specimen transport from (?:its|the) scope",
        r"clinical specimens?.*excluded from.*transport guideline",
    ]

    replacement = (
        "The MOH guideline covers transport of clinical specimens and infectious substances; "
        "clinical waste and chemical waste are outside that guideline's scope."
    )

    def fix(s: str, field: str) -> str:
        original = s
        for pat in bad_patterns:
            s = re.sub(pat, replacement, s, flags=re.I)
        if s != original:
            changes.append(f"RETRIEVED_CLAIM_SEMANTIC_CONSISTENCY:{field}:CLM-028")
        return s

    repaired["conclusion"] = fix(str(repaired.get("conclusion") or ""), "conclusion")
    for field in ("missing_information", "recommended_next_step", "limitations"):
        vals = list(repaired.get(field) or [])
        if vals:
            repaired[field] = [fix(str(v), field) for v in vals]

    # Remove unsupported recommendation to seek MOH "approval to classify"
    # when no retrieved evidence supports such an approval mechanism.
    recs = list(repaired.get("recommended_next_step") or [])
    new_recs = []
    for r in recs:
        s = str(r)
        if re.search(r"obtain formal approval from .*ministry of health.*classif", s, flags=re.I):
            changes.append("RETRIEVED_CLAIM_SEMANTIC_CONSISTENCY:removed_unsupported_MOH_classification_approval")
            new_recs.append(
                "Confirm the specimen classification and transport requirements using the applicable MOH guidance and supporting project information."
            )
        else:
            new_recs.append(s)
    if recs:
        repaired["recommended_next_step"] = new_recs

    return repaired, list(dict.fromkeys(changes))
