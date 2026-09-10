from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from .claim_reconciliation import (
    CLAIM_REVIEW_COMPLETE,
    build_claim_reconciliation_artifacts,
)
from .components import CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


DECISION_PACKET_VERSION = "BioSafe_Claim_Review_Decision_Packet_v0.1"
DECISION_REPORT_VERSION = "BioSafe_Claim_Review_Decision_Report_v0.1"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
HUMAN_REVIEW_COMPLETE = "HUMAN_REVIEW_COMPLETE"
DECISION_FIELDS = {
    "review_status", "disposition", "atomic_propositions", "support_spans",
    "authority_tier", "jurisdiction", "evidence_role", "currentness_status",
    "supersession_status", "allowed_decision_types", "allowed_actions",
    "limitations", "exclusions", "reviewer_identity", "reviewer_role",
    "review_date", "findings", "check_results", "attestations",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def apply_claim_decisions(
    review_map: dict[str, Any],
    review_map_bytes: bytes,
    decision_packet: dict[str, Any],
    decision_packet_bytes: bytes,
    crosswalk: dict[str, Any],
    crosswalk_bytes: bytes,
    knowledge_base: dict[str, Any],
    knowledge_base_bytes: bytes,
    components: dict[str, Any],
    component_bytes: bytes,
    fallbacks: dict[str, Any],
    fallback_bytes: bytes,
    fallback_reviews: dict[str, Any],
    fallback_review_bytes: bytes,
    applied_date: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        date.fromisoformat(applied_date)
    except (TypeError, ValueError) as error:
        raise ValidationError("applied date must be an ISO calendar date") from error
    build_claim_reconciliation_artifacts(
        crosswalk, crosswalk_bytes, review_map,
        knowledge_base, knowledge_base_bytes,
        components, component_bytes,
        fallbacks, fallback_bytes,
        fallback_reviews, fallback_review_bytes,
    )
    if decision_packet.get("decision_packet_version") != DECISION_PACKET_VERSION:
        raise ValidationError("claim decision packet version is invalid")
    if decision_packet.get("human_review_status") != HUMAN_REVIEW_COMPLETE:
        raise ValidationError("claim decision packet requires completed human review")
    if decision_packet.get("source_review_map_sha256") != sha256(review_map_bytes):
        raise ValidationError("claim decision packet is not bound to the supplied review map")
    batch_id = decision_packet.get("batch_id")
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValidationError("claim decision packet batch_id must be non-empty")
    decisions = decision_packet.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        raise ValidationError("claim decision packet decisions must not be empty")
    declared_ids = decision_packet.get("claim_ids")
    decision_ids = [item.get("claim_id") for item in decisions]
    if (
        not isinstance(declared_ids, list)
        or declared_ids != sorted(declared_ids)
        or len(declared_ids) != len(set(declared_ids))
        or declared_ids != sorted(decision_ids)
    ):
        raise ValidationError("claim decision packet claim_ids must exactly match decisions")

    result = json.loads(json.dumps(review_map))
    reviews = {item["claim_id"]: item for item in result.get("claim_reviews", [])}
    before = json.loads(json.dumps(reviews))
    for decision in decisions:
        claim_id = decision.get("claim_id")
        if claim_id not in reviews:
            raise ValidationError(f"claim decision references unknown claim: {claim_id}")
        if set(decision) != DECISION_FIELDS | {"claim_id"}:
            raise ValidationError(f"claim decision fields are invalid for {claim_id}")
        review = reviews[claim_id]
        if review.get("review_status") != CLAIM_REVIEW_REQUIRED:
            raise ValidationError(f"claim review is not pending: {claim_id}")
        if decision.get("review_status") != CLAIM_REVIEW_COMPLETE:
            raise ValidationError(f"claim decision must complete review: {claim_id}")
        review.update({field: decision[field] for field in DECISION_FIELDS})

    changed_ids = sorted(
        claim_id for claim_id, review in reviews.items() if review != before[claim_id]
    )
    if changed_ids != declared_ids:
        raise ValidationError("claim decision application changed an unexpected claim set")

    packet, curated = build_claim_reconciliation_artifacts(
        crosswalk, crosswalk_bytes, result,
        knowledge_base, knowledge_base_bytes,
        components, component_bytes,
        fallbacks, fallback_bytes,
        fallback_reviews, fallback_review_bytes,
    )
    result_bytes = canonical_json_bytes(result)
    report = {
        "decision_report_version": DECISION_REPORT_VERSION,
        "batch_id": batch_id,
        "applied_date": applied_date,
        "source_review_map_sha256": sha256(review_map_bytes),
        "source_decision_packet_sha256": sha256(decision_packet_bytes),
        "result_review_map_sha256": sha256(result_bytes),
        "snapshot_sha256": sha256(review_map_bytes),
        "changed_claim_ids": changed_ids,
        "changed_claim_count": len(changed_ids),
        "disposition_counts": dict(sorted(Counter(
            reviews[claim_id]["disposition"] for claim_id in changed_ids
        ).items())),
        "total_completed_review_count": packet["completed_review_count"],
        "total_pending_review_count": (
            packet["required_review_count"] - packet["completed_review_count"]
        ),
        "total_curated_claim_count": curated["curated_claim_count"],
        "curated_claim_ids": [item["claim_id"] for item in curated["curated_claims"]],
        "claim_use_status": packet["claim_use_status"],
        "live_activation_status": packet["live_activation_status"],
    }
    return result, report


def write_bytes_atomic(data: bytes, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, output)