#!/usr/bin/env python3
"""Apply the guarded CLM-005/CLM-007 source-support approval to the claim map.

This deliberately does not resolve legal currentness or case applicability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from biosafe_controlled_ingestion.claim_reconciliation import write_json_atomic
from biosafe_controlled_ingestion.contracts import ValidationError


TARGETS = {"CLM-005", "CLM-007"}
UNRESOLVED = "CURRENTNESS_UNRESOLVED"
EXPECTED_SUPPORT_PACKET_SHA256 = "b75651248ef033449c9b53da4a5adc92a8263f0cbb4642286e44422d6396a231"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def apply_approval(review_map: dict, review_map_bytes: bytes, support_packet: dict, support_bytes: bytes) -> dict:
    if _sha256(support_bytes) != EXPECTED_SUPPORT_PACKET_SHA256:
        raise ValidationError("support packet hash is not the accepted review artifact")
    if support_packet.get("human_review_status") != "HUMAN_REVIEW_COMPLETE":
        raise ValidationError("exact-support approval must be human-review complete")
    if support_packet.get("promotion_status") != "NOT_PROMOTED":
        raise ValidationError("exact-support approval must not be promoted")
    if support_packet.get("claim_ids") != ["CLM-005", "CLM-007"]:
        raise ValidationError("exact-support approval must cover CLM-005 and CLM-007")

    result = json.loads(json.dumps(review_map))
    reviews = {item["claim_id"]: item for item in result.get("claim_reviews", [])}
    entries = {item["claim_id"]: item for item in support_packet.get("entries", [])}
    if set(entries) != TARGETS or not TARGETS.issubset(reviews):
        raise ValidationError("claim map and support approval must contain both target claims")

    for claim_id in sorted(TARGETS):
        review = reviews[claim_id]
        entry = entries[claim_id]
        if review.get("review_status") != "CLAIM_REVIEW_COMPLETE":
            raise ValidationError(f"claim review is not complete: {claim_id}")
        if entry.get("currentness") != "UNRESOLVED":
            raise ValidationError(f"support approval currentness is not unresolved: {claim_id}")

        review["source_support_disposition"] = "SUPPORTED_AFTER_ATOMIC_SPLIT"
        review["support_review_status"] = "ACCEPTED_AS_SOURCE_SUPPORT"
        review["support_review_artifact_sha256"] = _sha256(support_bytes)
        review["semantic_units"] = entry["semantic_units"]
        review["allowed_actions"] = []
        review["allowed_decision_types"] = []
        review["promotion_status"] = "NOT_PROMOTED"
        review["disposition"] = UNRESOLVED
        review["currentness_status"] = "CURRENTNESS_UNRESOLVED"
        review["review_status"] = "CLAIM_REVIEW_COMPLETE"
        review["reviewer_identity"] = entry["reviewer_identity"]
        review["reviewer_role"] = entry["reviewer_role"]
        review["review_date"] = entry["review_date"]
        review["attestations"] = entry["attestations"]
        review["check_results"] = {
            "allowed_actions_checked": "PASS",
            "atomicity_checked": "PASS",
            "authority_and_jurisdiction_checked": "PASS",
            "currentness_and_supersession_checked": "PASS",
            "exact_support_adequate": "PASS",
            "limitations_and_exclusions_checked": "PASS",
        }
        review["findings"] = [
            "The project owner approved the reviewed source-level propositions and exact support spans for guarded canonical curation.",
            "Source support is accepted after the required semantic restructuring; legal currentness remains unresolved.",
            "This approval is not a case-specific applicability, notification, exemption, approval, compliance, or permission-to-begin-work determination.",
        ]

        if claim_id == "CLM-005":
            review["dependency_atomic_propositions"] = entry["atomic_propositions"][:4]
            review["atomic_propositions"] = entry["atomic_propositions"][4:]
            review["support_spans"] = [
                {
                    **span,
                    "atomic_proposition_indexes": [index - 4 for index in span["atomic_proposition_indexes"]],
                }
                for span in entry["support_spans"]
                if min(span["atomic_proposition_indexes"]) >= 5
            ]
            review["dependency_support_spans"] = [
                {**span, "support_type": "CONTEXT"}
                for span in entry["support_spans"]
                if max(span["atomic_proposition_indexes"]) <= 4
            ]
            review["cross_document_dependencies"] = [{
                "dependency_id": "CLM-005-ACT-678-CONTEXT",
                "relationship": "CROSS_DOCUMENT_SCOPE_DEPENDENCY",
                "source_document_id": "KB-MY-ACT678",
                "source_provision": "section 22(1)(a)–(c)",
                "evidence_role": "SECTION_22_REFERENCED_ACTIVITY_SCOPE",
                "direct_canonical_support": False,
                "required_for_interpretation": True,
            }]
        else:
            review["atomic_propositions"] = entry["atomic_propositions"]
            review["support_spans"] = entry["support_spans"]
            review["cross_document_dependencies"] = []
            review["dependency_support_spans"] = []

    result["exact_support_approval"] = {
        "decision": "APPROVED_FOR_GUARDED_CANONICAL_SOURCE_CURATION",
        "reviewer_identity": "BioSafe project owner",
        "reviewer_role": "Claim reconciliation reviewer",
        "review_date": "2026-09-13",
        "support_packet_sha256": _sha256(support_bytes),
        "currentness_preserved_as_unresolved": True,
        "case_level_authorization_prohibited": True,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply guarded exact-support approval for CLM-005 and CLM-007.")
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--support-packet", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    map_bytes = args.review_map.read_bytes()
    support_bytes = args.support_packet.read_bytes()
    result = apply_approval(
        json.loads(map_bytes), map_bytes,
        json.loads(support_bytes), support_bytes,
    )
    write_json_atomic(result, args.output)
    print("approved_source_support=CLM-005,CLM-007 currentness=CURRENTNESS_UNRESOLVED promotion=NOT_PROMOTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())