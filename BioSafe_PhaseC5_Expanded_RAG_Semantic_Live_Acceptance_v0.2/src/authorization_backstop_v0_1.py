from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
VOCABULARY_PATH=HERE/"authorization_vocabulary_v0_1.json"

FAIL_CLOSED_MESSAGE=(
    "BioSafe cannot determine whether a permit, approval, licence, exemption, or other "
    "authorization is required for the described activity without sufficient project-specific "
    "facts and reviewed regulatory evidence."
)

AUTHORIZATION_NOUNS="(?:permit|licence|license|approval|authorization|authorisation|exemption|notification)"
POSITIVE_PATTERNS=(
    re.compile(rf"\byou need (?:a |an |to )?(?:biosafety |biosecurity )?{AUTHORIZATION_NOUNS}",re.I),
    re.compile(rf"\b{AUTHORIZATION_NOUNS} is required",re.I),
    re.compile(rf"\byou (?:must|need to) (?:obtain|submit|apply for)\b[^.!?\n]*{AUTHORIZATION_NOUNS}",re.I),
)

NOUN_PATTERNS={
    "permit":re.compile(r"\bpermit",re.I),
    "approval":re.compile(r"\bapproval",re.I),
    "authorization":re.compile(r"\bauthori[sz]ation",re.I),
    "licence":re.compile(r"\blicen[cs]e",re.I),
    "exemption":re.compile(r"\bexemption",re.I),
    "notification":re.compile(r"\bnotification",re.I),
}

SENTENCE_SPLIT=re.compile(r"(?<=[.!?])\s+")

TEXT_FIELDS=("conclusion","direct_answer")
LIST_FIELDS=("recommended_next_step","recommendations","recommended_next_steps")


def load_support_types(path: Path=VOCABULARY_PATH) -> dict[str, list[str]]:
    vocabulary=json.loads(path.read_text(encoding="utf-8"))
    support=vocabulary.get("authorization_claim_support_types")
    if not isinstance(support,dict) or not support:
        raise ValueError("authorization vocabulary missing authorization_claim_support_types")
    return support


_SUPPORT_CACHE: dict[str, list[str]]|None=None


def _support_types() -> dict[str, list[str]]:
    global _SUPPORT_CACHE
    if _SUPPORT_CACHE is None:
        _SUPPORT_CACHE=load_support_types()
    return _SUPPORT_CACHE


def _split_sentences(text: str) -> list[str]:
    return [s for s in SENTENCE_SPLIT.split(text or "") if s.strip()]


def _claim_nouns(sentence: str) -> list[str]:
    return [noun for noun,pattern in NOUN_PATTERNS.items() if pattern.search(sentence)]


def _supported(nouns: list[str], evidence_bundle: list[dict[str, Any]]) -> bool:
    """A claim is supported only when at least one evidence item's claim_type
    explicitly references the same authorization requirement for every noun
    asserted in the sentence."""
    support=_support_types()
    claim_types={str(item.get("claim_type") or "").strip().lower() for item in evidence_bundle or []}
    for noun in nouns:
        acceptable=set(support.get(noun,[]))
        if not acceptable:
            return False
        if not (acceptable & claim_types):
            return False
    return True


def _screen(text: str, evidence_bundle: list[dict[str, Any]]) -> tuple[list[str],list[str]]:
    kept: list[str]=[]; removed: list[str]=[]
    for sentence in _split_sentences(text):
        if any(pattern.search(sentence) for pattern in POSITIVE_PATTERNS):
            nouns=_claim_nouns(sentence)
            if nouns and not _supported(nouns,evidence_bundle):
                removed.append(sentence.strip())
                continue
        kept.append(sentence)
    return kept,removed


def apply_authorization_backstop(response: dict[str, Any], evidence_bundle: list[dict[str, Any]] | None=None) -> tuple[dict[str, Any],list[dict[str, Any]]]:
    """Deterministic post-generation guard for high-stakes authorization output.

    Model output is untrusted: any positive authorization claim whose requirement
    type is not explicitly present in the scoped evidence claim_types is removed
    and replaced with the deterministic fail-closed message. Returns the guarded
    response and a structured audit list.
    """
    guarded=dict(response)
    bundle=evidence_bundle if evidence_bundle is not None else list(guarded.get("evidence") or [])
    audit: list[dict[str, Any]]=[]
    for field in TEXT_FIELDS:
        value=guarded.get(field)
        if not isinstance(value,str) or not value.strip():
            continue
        kept,removed=_screen(value,bundle)
        if not removed:
            continue
        guarded[field]=FAIL_CLOSED_MESSAGE
        for claim in removed:
            audit.append({
                "action":"unsupported_authorization_claim_removed",
                "field":field,
                "claim":claim,
                "reason_codes":["NO_EVIDENCE_SUPPORT"],
                "replacement":FAIL_CLOSED_MESSAGE,
            })
    for field in LIST_FIELDS:
        value=guarded.get(field)
        if not isinstance(value,list):
            continue
        new_items: list[Any]=[]
        for item in value:
            if isinstance(item,str) and item.strip():
                kept,removed=_screen(item,bundle)
                if removed:
                    for claim in removed:
                        audit.append({
                            "action":"unsupported_authorization_claim_removed",
                            "field":field,
                            "claim":claim,
                            "reason_codes":["NO_EVIDENCE_SUPPORT"],
                            "replacement":FAIL_CLOSED_MESSAGE,
                        })
                    continue
            new_items.append(item)
        guarded[field]=new_items
    if audit:
        safety=dict(guarded.get("safety") or {})
        safety["status"]="FAIL_CLOSED"
        safety["response_mode"]="ask_before_concluding"
        codes=list(safety.get("reason_codes") or [])
        codes.append("UNSUPPORTED_AUTHORIZATION_CLAIM_REMOVED")
        safety["reason_codes"]=codes
        guarded["safety"]=safety
        meta=dict(guarded.get("_meta") or {})
        meta["authorization_backstop"]=[{"action":item["action"],"field":item["field"],"claim":item["claim"],"reason_codes":item["reason_codes"]} for item in audit]
        guarded["_meta"]=meta
    return guarded,audit
