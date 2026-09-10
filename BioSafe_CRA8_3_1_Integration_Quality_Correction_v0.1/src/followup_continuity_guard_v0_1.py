from __future__ import annotations
import re
from typing import Any, Optional

REFERENTIAL_PATTERNS = [
    r"^\s*why\??\s*$",
    r"^\s*why does (that|this|it) matter\??\s*$",
    r"^\s*what about (that|this|it)\??\s*$",
    r"^\s*how about (that|this|it)\??\s*$",
    r"^\s*what does (that|this|it) mean\??\s*$",
    r"^\s*can you explain (that|this|it)\??\s*$",
    r"^\s*explain (that|this|it)\??\s*$",
    r"^\s*and (that|this|it)\??\s*$",
]

def is_referential_followup(text: str) -> bool:
    t=(text or "").strip().lower()
    if not t:
        return False
    if any(re.search(p,t,re.I) for p in REFERENTIAL_PATTERNS):
        return True
    # General short-turn fallback: demonstrative/pronoun reference plus explanation cue.
    tokens=t.split()
    if len(tokens) <= 8 and any(x in t for x in ("that","this","it")) and any(
        cue in t for cue in ("why","matter","mean","explain","about","how")
    ):
        return True
    return False

def derive_reference_from_state(conversation: Any, case: Any) -> Optional[str]:
    concepts=getattr(conversation,"assistant_concepts",None) or []
    if concepts:
        last=concepts[-1]
        if isinstance(last,str):
            return last
        for attr in ("concept","label","name","text","value"):
            v=getattr(last,attr,None)
            if isinstance(v,str) and v.strip():
                return v.strip()
        if isinstance(last,dict):
            for k in ("concept","label","name","text","value"):
                v=last.get(k)
                if isinstance(v,str) and v.strip():
                    return v.strip()

    active=getattr(case,"active_domains",None) or []
    if active:
        return str(active[-1])
    return None

def apply_followup_continuity(
    text: str,
    interaction: Any,
    conversation: Any,
    case: Any,
    resolved_reference: Optional[str],
):
    """
    Returns (interaction, resolved_reference, inherited_domains, changed).

    This is deliberately structural:
    - it does not answer the follow-up;
    - it does not invent domain facts;
    - it only repairs turn classification/reference continuity when the text
      is clearly referential and prior state exists.
    """
    if not is_referential_followup(text):
        return interaction,resolved_reference,[],False

    inherited=list(getattr(case,"active_domains",None) or [])
    if not inherited and not resolved_reference:
        return interaction,resolved_reference,[],False

    # Preserve the existing InteractionResult object where possible.
    try:
        from cra_contracts_v0_1 import InteractionType
        setattr(interaction,"interaction_type",InteractionType.FOLLOW_UP)
    except Exception:
        pass

    ref=resolved_reference or derive_reference_from_state(conversation,case)
    return interaction,ref,inherited,True
