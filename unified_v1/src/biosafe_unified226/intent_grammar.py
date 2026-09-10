"""
Structural intent grammar (Layers 1-2 of the conversational architecture).

This replaces string-enumerated intent matching with a three-step pipeline:

  Layer 1 - canonicalize(): normalize surface text (case, punctuation, contractions,
            polite fillers) so that paraphrase variance collapses.
  Layer 2 - parse_act(): classify the utterance *structure* into a small fixed set of
            conversation acts (greeting, product_help, self_knowledge, definition,
            difference, elaboration, continuation, image_query, document_review,
            regulatory_assessment, simple_answer).

The grammar is fixed and small; new phrasings match through structure rather than
enumeration. Anything that cannot be classified confidently falls through to
"simple_answer", which the downstream pipeline (RAG + LLM + guards) handles.

This module is advisory (non-frozen). It never makes regulatory or safety decisions;
it only decides *what kind of conversational turn* the user has produced and *what
subject* they are referring to, so that deterministic handlers and the model can
respond appropriately.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Layer 1 - canonicalization
# ---------------------------------------------------------------------------

_CONTRACTIONS = {
    "whats": "what is",
    "what're": "what are",
    "what's": "what is",
    "its": "it is",
    "it's": "it is",
    "that's": "that is",
    "doesnt": "does not",
    "don't": "do not",
    "dont": "do not",
    "isnt": "is not",
    "isn't": "is not",
    "cant": "can not",
    "can't": "can not",
    "wont": "will not",
    "won't": "will not",
    "wouldnt": "would not",
    "wouldn't": "would not",
    "im": "i am",
    "i'm": "i am",
    "ive": "i have",
    "i've": "i have",
    "id": "i would",
    "i'd": "i would",
    "youre": "you are",
    "you're": "you are",
    "u": "you",
    "r": "are",
    "ur": "your",
}

# Polite / conversational filler phrases stripped when they appear at the start.
_FILLER_PREFIXES = (
    "please ",
    "can you ",
    "could you ",
    "would you ",
    "so ",
    "just ",
    "i want to ",
    "i'd like to ",
    "i would like to ",
    "help me ",
    "i need to ",
    "tell me ",
)
def canonicalize(text: str) -> str:
    """Normalize surface text: lowercase, expand contractions, strip punctuation."""
    s = (text or "").strip().lower()
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    # split into tokens so we can expand contractions on word boundaries
    tokens = re.findall(r"[a-z']+", s)
    out = []
    for tok in tokens:
        out.append(_CONTRACTIONS.get(tok, tok))
    s = " ".join(out)
    # collapse multiple spaces and strip trailing punctuation
    s = re.sub(r"\s+", " ", s).strip()
    s = s.rstrip("?.!")
    return s


def strip_fillers(text: str) -> str:
    """Return text with leading polite/conversational fillers removed."""
    t = (text or "").strip()
    changed = True
    while changed:
        changed = False
        for f in _FILLER_PREFIXES:
            if t.lower().startswith(f) and len(t) > len(f):
                t = t[len(f):].strip()
                changed = True
                break
    return t


# ---------------------------------------------------------------------------
# Layer 2 - structural act classification
# ---------------------------------------------------------------------------

_GREETING = re.compile(
    r"^(hi|hello|hey|yo|good (morning|afternoon|evening)|greetings|howdy)\b[\s,!.:-]*",
    re.I,
)

_DEFINITION = re.compile(
    r"^(?:what(?:'s| is| are)|what do (?:you )?mean by|define|explain|"
    r"meaning of|what does|what is meant by)\s+(.+?)$",
    re.I,
)

_DIFFERENCE = re.compile(
    r"^.*?difference (?:between|of)\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+?)$",
    re.I,
)

_ELABORATION = re.compile(
    r"^(?:please\s+)?(?:elaborate|explain more|explain further|more detail|"
    r"go deeper|expand|tell me more|give (?:me )?(?:an? )?example|"
    r"(?:can you )?(?:create|use)\b.{0,50}\b(?:general )?(?:case|example)|"
    r"case stud(?:y|ies)|i want to (?:know|understand) more|"
    r"please (?:explain|elaborate)).*$",
    re.I,
)

_CONTINUATION = re.compile(
    r"^(?:i just want to (?:understand|learn|know)|help me understand|"
    r"i want to (?:learn|understand) more|let me (?:understand|learn)|"
    r"i (?:want|need) to (?:learn|understand) (?:this|that|more)).*$",
    re.I,
)

_PRODUCT_HELP = re.compile(
    r"^(?:who are you|what are you|what can you do|what do you do|"
    r"tell me about yourself|how (?:can|do) you help|what is your purpose|"
    r"what are your capabilities|what are you capable of).*$",
    re.I,
)

_SELF_KNOWLEDGE = re.compile(
    r"^(?:do you know (?:who|what) i am|do you know me|who am i|"
    r"what do you know about me|do you remember me).*$",
    re.I,
)

_IMAGE_QUERY = re.compile(
    r"\b(?:this image|the image|this photo|the photo|this picture|the picture|"
    r"this screenshot|the screenshot|this attachment|the attachment|"
    r"this uploaded|the uploaded|what is in this image|look at this image)\b",
    re.I,
)

_DOC_REVIEW = re.compile(
    r"^(?:review|assess|check|evaluate|read|look at|analyze)\s+(?:this|the|my|"
    r"that|an?)\s+(?:document|file|sop|protocol|form|report|attachment).*$",
    re.I,
)

_REGULATORY = re.compile(
    r"\b(?:regulat|law|legal|permit|approval|approve|notify|notification|"
    r"comply|compliance|requirement|required|act 678|biosafety act|"
    r"director general|form e|consent|authori[sz]ation)\b",
    re.I,
)
# Curated knowledge concepts with non-regulatory educational answers. More
# consequential concepts may still be recognized below, but service-level
# deterministic rendering is allow-listed separately and otherwise falls
# through to authoritative retrieval.
CONCEPT_ALIASES = {
    "biosafety": ["biosafety", "bio safety"],
    "biosecurity": ["biosecurity", "bio security"],
    "biosafety_vs_biosecurity": [
        "biosafety and biosecurity", "difference between biosafety and biosecurity",
    ],
    "risk_group": ["risk group", "biological risk group", "risk groups"],
    "bsl": ["biosafety level", "bsl", "containment level", "containment"],
    "lmo": ["lmo", "living modified organism", "genetically modified organism", "gmo"],
    "form_e": ["form e", "biosafety form e"],
    "bwc": ["biological weapons convention"],
    "pi_ibc": ["pi and ibc", "principal investigator", "institutional biosafety committee"],
}

DETERMINISTIC_EDUCATIONAL_CONCEPTS = frozenset({
    "biosafety",
    "biosecurity",
    "biosafety_vs_biosecurity",
})


def _resolve_concept(subject: str) -> Optional[str]:
    """Map an extracted subject to a Layer-3 concept key, or None.

    Exact alias matches win; otherwise the subject may contain an alias as a
    whole phrase. This keeps "biosafety" on the simple concept while
    "biosafety and biosecurity" resolves to the combined concept.
    """
    s = canonicalize(subject).strip()
    best: Optional[str] = None
    best_len = -1
    for key, aliases in CONCEPT_ALIASES.items():
        for alias in aliases:
            score = -1
            if s == alias:
                # exact match: highest priority
                score = 10_000 + len(alias)
            elif re.search(rf"\b{re.escape(alias)}\b", s):
                # subject is a longer phrase containing the alias as a whole phrase
                score = len(alias)
            if score > best_len:
                best = key
                best_len = score
    return best


def parse_act(query: str, attachments: Optional[List[Dict[str, Any]]] = None,
              previous_subject: Optional[str] = None,
              previous_concept: Optional[str] = None) -> Dict[str, Any]:
    """
    Classify a user utterance into a conversation act plus an optional subject.

    Returns a dict with keys:
      act: one of greeting, product_help, self_knowledge, image_query, definition,
           difference, elaboration, continuation, document_review,
           regulatory_assessment, simple_answer
      subject: extracted subject (for definition/difference), else None
      concept: resolved Layer-3 concept key, else None
      bound_subject: subject resolved from previous turn (for continuation/elaboration)
    """
    attachments = attachments or []
    raw = (query or "").strip()
    q = strip_fillers(canonicalize(raw))

    result: Dict[str, Any] = {
        "act": "simple_answer",
        "subject": None,
        "concept": None,
        "bound_subject": None,
    }

    # Image queries take priority: the user is asking about an uploaded image.
    if _IMAGE_QUERY.search(raw) and any(
        a.get("is_image") or a.get("image") for a in attachments
    ):
        result["act"] = "image_query"
        return result

    # Empty/meaningless
    if not q:
        if attachments:
            result["act"] = "document_review"
        return result

    # Greeting (with optional trailing content, e.g. "hi, what can you do")
    if _GREETING.match(q):
        rest = _GREETING.sub("", q).strip()
        if rest:
            inner = parse_act(rest, attachments, previous_subject)
            result["act"] = inner.get("act", "simple_answer")
            result["subject"] = inner.get("subject")
            result["concept"] = inner.get("concept")
            result["bound_subject"] = inner.get("bound_subject")
            if result["act"] == "simple_answer":
                result["act"] = "greeting"
            return result
        result["act"] = "greeting"
        return result

    # Self-knowledge / product-help before generic definition so "what are you" wins
    if _SELF_KNOWLEDGE.match(q):
        result["act"] = "self_knowledge"
        return result
    if _PRODUCT_HELP.match(q):
        result["act"] = "product_help"
        return result

    # Difference between X and Y
    m = _DIFFERENCE.search(q)
    if m:
        result["act"] = "difference"
        left = _resolve_concept(m.group(1))
        right = _resolve_concept(m.group(2))
        # biosafety vs biosecurity maps to the combined concept
        if left and right:
            result["concept"] = f"{left}_vs_{right}"
        elif left or right:
            result["concept"] = left or right
        result["subject"] = canonicalize(f"{m.group(1)} vs {m.group(2)}")
        return result

    # Definition: what is X / define X / explain X
    m = _DEFINITION.match(q)
    if m:
        subject = m.group(1).strip()
        result["act"] = "definition"
        result["subject"] = subject
        result["concept"] = _resolve_concept(subject)
        return result

    # Document review
    if _DOC_REVIEW.match(q) or (attachments and not q):
        result["act"] = "document_review"
        return result

    # Continuation / elaboration resolve the subject from the previous turn
    if _CONTINUATION.match(q) or _ELABORATION.match(q):
        # try to bind to a concept named inline first
        inline = _resolve_concept(q)
        if inline:
            result["concept"] = inline
            result["act"] = "definition"
            return result
        if previous_concept:
            result["bound_subject"] = previous_subject
            result["concept"] = previous_concept
            result["act"] = "definition" if _CONTINUATION.match(q) else "elaboration"
            return result
        if previous_subject:
            bound = _resolve_concept(previous_subject)
            result["bound_subject"] = previous_subject
            result["concept"] = bound
            result["act"] = "definition" if _CONTINUATION.match(q) else "elaboration"
            return result
        result["act"] = "elaboration"
        return result

    # Regulatory assessment
    if _REGULATORY.search(q):
        result["act"] = "regulatory_assessment"
        return result

    return result