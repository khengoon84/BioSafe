import re
from typing import Optional
from cra_contracts_v0_1 import ConversationState

ORDINAL_MAP={"first":0,"second":1,"third":2}
GENERIC_REFERENTS = r"\b(?:that|it|this|approval|requirement|regulation|rule|form|document|notification|pathway)\b"

def resolve_reference(text: str, state: ConversationState) -> Optional[str]:
    t=(text or "").strip().lower()
    concepts=state.recent_assistant_concepts
    if not concepts:
        return None

    m=re.search(r"\b(first|second|third)\s+(?:one|point)\b",t)
    if m:
        idx=ORDINAL_MAP[m.group(1)]
        if len(concepts)>idx:
            return concepts[idx].concept_id

    # Prefer semantic overlap with a concept label.
    for c in reversed(concepts):
        label=(c.label or "").lower()
        tokens=[x for x in re.findall(r"[a-z0-9]+",label) if len(x)>3]
        if any(tok in t for tok in tokens):
            return c.concept_id

    # Generalized anaphora: a follow-up that uses a generic concept noun
    # refers to the most recent assistant concept unless better evidence exists.
    if re.search(GENERIC_REFERENTS,t):
        return concepts[-1].concept_id

    if re.fullmatch(r"\s*why[?.! ]*",t):
        return concepts[-1].concept_id
    return None
