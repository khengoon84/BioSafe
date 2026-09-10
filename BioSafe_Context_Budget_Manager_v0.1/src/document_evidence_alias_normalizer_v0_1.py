
from __future__ import annotations
from typing import Any

def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())

def normalize_document_evidence_aliases(
    output: dict[str, Any],
    evidence_bundle: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    if not isinstance(output, dict):
        return output, []

    repaired = dict(output)
    evidence = list(repaired.get("evidence") or [])
    by_filename: dict[str, list[dict[str, Any]]] = {}

    for ev in evidence_bundle or []:
        if ev.get("record_type") == "user_document" and ev.get("document_id") and ev.get("evidence_id"):
            by_filename.setdefault(ev["document_id"], []).append(ev)

    changes = []
    new_evidence = []
    for item in evidence:
        if not isinstance(item, dict):
            new_evidence.append(item)
            continue

        item2 = dict(item)
        eid = item2.get("evidence_id")
        statement = _norm(str(item2.get("statement") or ""))

        if eid in by_filename:
            candidates = by_filename[eid]
            match = None
            for ev in candidates:
                txt = _norm(str(ev.get("text") or ""))
                if statement and txt and (statement == txt or statement in txt or txt in statement):
                    match = ev
                    break
            if match is None and len(candidates) == 1:
                match = candidates[0]

            if match is not None:
                old = eid
                item2["evidence_id"] = match["evidence_id"]
                changes.append(f"DOCUMENT_EVIDENCE_ALIAS: {old} -> {match['evidence_id']}")

        new_evidence.append(item2)

    repaired["evidence"] = new_evidence
    return repaired, changes
