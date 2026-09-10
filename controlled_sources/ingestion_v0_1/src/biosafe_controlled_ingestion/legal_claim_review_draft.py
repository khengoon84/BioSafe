from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .claim_reconciliation import write_json_atomic
from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


DRAFT_MAP_VERSION = "BioSafe_Legal_Claim_Review_Draft_Map_v0.1"
DRAFT_ARTIFACT_VERSION = "BioSafe_Legal_Claim_Review_Draft_v0.1"
DRAFT_SCOPE = "HUMAN_REVIEW_NAVIGATION_AND_ATOMIZATION_AID_ONLY"
LEGAL_CLAIM_IDS = {
    "CLM-001", "CLM-002", "CLM-003", "CLM-004", "CLM-005",
    "CLM-006", "CLM-007", "CLM-029", "CLM-030",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalized(text: str) -> str:
    return " ".join(text.split()).casefold()


def _require_text(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")


def build_legal_claim_review_draft(
    draft_map: dict[str, Any],
    draft_map_bytes: bytes,
    reconciliation_map: dict[str, Any],
    reconciliation_map_bytes: bytes,
    source_policy: dict[str, Any],
    source_policy_bytes: bytes,
    component_artifact: dict[str, Any],
    component_artifact_bytes: bytes,
) -> dict[str, Any]:
    if draft_map.get("draft_map_version") != DRAFT_MAP_VERSION:
        raise ValidationError("legal claim draft map version is invalid")
    if draft_map.get("draft_scope") != DRAFT_SCOPE:
        raise ValidationError("legal claim draft map scope is invalid")
    for name, artifact in (("draft map", draft_map), ("reconciliation map", reconciliation_map), ("component artifact", component_artifact)):
        if artifact.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
            raise ValidationError(f"{name} must require claim review")
        if artifact.get("live_activation_status") != ACTIVATION_PROHIBITED:
            raise ValidationError(f"{name} must prohibit live activation")
    reviews = {item["claim_id"]: item for item in reconciliation_map.get("claim_reviews", [])}
    policies = source_policy.get("sources", {})
    candidates = {item["candidate_chunk_id"]: item for item in component_artifact.get("candidate_chunks", [])}
    drafts = draft_map.get("drafts")
    if not isinstance(drafts, list):
        raise ValidationError("legal claim drafts must be a list")
    seen: set[str] = set()
    items = []
    for draft in drafts:
        claim_id = draft.get("claim_id")
        if claim_id in seen or claim_id not in LEGAL_CLAIM_IDS or claim_id not in reviews:
            raise ValidationError("legal draft must contain unique known legal claim IDs")
        seen.add(claim_id)
        review = reviews[claim_id]
        if review["review_status"] != CLAIM_REVIEW_REQUIRED:
            raise ValidationError("legal draft may only describe pending claim reviews")
        chunk_ids = draft.get("candidate_chunk_ids")
        if not isinstance(chunk_ids, list) or not chunk_ids:
            raise ValidationError("legal draft must include candidate chunk IDs")
        selected = []
        combined = ""
        for chunk_id in chunk_ids:
            candidate = candidates.get(chunk_id)
            if candidate is None:
                raise ValidationError(f"legal draft candidate does not exist: {chunk_id}")
            if candidate["document_id"] != review["controlled_document_id"]:
                raise ValidationError(f"legal draft candidate document mismatch for {claim_id}")
            if candidate["source_sha256"] != review["controlled_source_sha256"]:
                raise ValidationError(f"legal draft candidate hash mismatch for {claim_id}")
            selected.append(candidate)
            combined += "\n" + candidate["text"]
        phrases = draft.get("locator_phrases")
        if not isinstance(phrases, list) or not phrases:
            raise ValidationError("legal draft locator phrases must not be empty")
        normalized = _normalized(combined)
        for phrase in phrases:
            _require_text("legal draft locator phrase", phrase)
            if _normalized(phrase) not in normalized:
                raise ValidationError(f"legal draft locator phrase is absent for {claim_id}: {phrase}")
        for field in ("draft_atomic_propositions", "review_issues", "currentness_blockers"):
            values = draft.get(field)
            if not isinstance(values, list) or not values:
                raise ValidationError(f"legal draft {field} must not be empty")
            for value in values:
                _require_text(f"legal draft {field} item", value)
        policy = policies.get(review["controlled_document_id"])
        if not isinstance(policy, dict):
            raise ValidationError(f"legal draft source policy is missing for {claim_id}")
        if policy.get("supersession_status") not in draft["currentness_blockers"]:
            raise ValidationError(f"legal draft omits controlled supersession blocker for {claim_id}")
        items.append({
            "claim_id": claim_id,
            "original_claim": review["original_claim"],
            "controlled_document_id": review["controlled_document_id"],
            "controlled_source_sha256": review["controlled_source_sha256"],
            "claim_review_status": review["review_status"],
            "controlled_currentness_status": policy["currentness_status"],
            "controlled_supersession_status": policy["supersession_status"],
            "candidate_evidence": [{
                "candidate_chunk_id": item["candidate_chunk_id"],
                "source_sha256": item["source_sha256"],
                "pdf_page_start": item["pdf_page_start"],
                "pdf_page_end": item["pdf_page_end"],
                "text": item["text"],
            } for item in selected],
            "locator_phrases": phrases,
            "draft_atomic_propositions": draft["draft_atomic_propositions"],
            "review_issues": draft["review_issues"],
            "currentness_blockers": draft["currentness_blockers"],
            "draft_disposition": None,
            "automated_claim_update": None,
            "reviewer_identity": None,
            "reviewer_attestations": None,
        })
    if seen != LEGAL_CLAIM_IDS:
        raise ValidationError("legal draft map must cover the exact nine legal claims")
    return {
        "artifact_version": DRAFT_ARTIFACT_VERSION,
        "source_draft_map_sha256": _sha256(draft_map_bytes),
        "source_claim_reconciliation_map_sha256": _sha256(reconciliation_map_bytes),
        "source_policy_sha256": _sha256(source_policy_bytes),
        "source_component_artifact_sha256": _sha256(component_artifact_bytes),
        "artifact_scope": DRAFT_SCOPE,
        "legal_claim_count": len(items),
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "live_activation_status": ACTIVATION_PROHIBITED,
        "draft_dispositions_present": 0,
        "legal_claim_drafts": sorted(items, key=lambda item: item["claim_id"]),
    }


def write_legal_claim_review_draft(artifact: dict[str, Any], output: Path) -> None:
    write_json_atomic(artifact, output)