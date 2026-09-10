#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.claim_reconciliation import (
    CLAIM_REVIEW_COMPLETE,
    write_json_atomic,
)
from biosafe_controlled_ingestion.legal_claim_review_draft import LEGAL_CLAIM_IDS


def apply_review(
    review_map: dict,
    legal_draft: dict,
    *,
    reviewer_identity: str,
    reviewer_role: str,
    review_date: str,
) -> dict:
    drafts = {item["claim_id"]: item for item in legal_draft["legal_claim_drafts"]}
    if set(drafts) != LEGAL_CLAIM_IDS:
        raise ValueError("legal review draft must cover the exact nine legal claims")
    result = json.loads(json.dumps(review_map))
    reviews = {item["claim_id"]: item for item in result["claim_reviews"]}
    for claim_id in sorted(LEGAL_CLAIM_IDS):
        review = reviews[claim_id]
        draft = drafts[claim_id]
        if review["review_status"] != "REVIEW_REQUIRED_BEFORE_CLAIM_USE":
            raise ValueError(f"legal claim is not pending: {claim_id}")
        review.update({
            "review_status": CLAIM_REVIEW_COMPLETE,
            "disposition": "CURRENTNESS_UNRESOLVED",
            "atomic_propositions": draft["draft_atomic_propositions"],
            "support_spans": [],
            "authority_tier": "Tier 1",
            "jurisdiction": "Malaysia",
            "evidence_role": "BASE_INSTRUMENT_REVIEW_CURRENTNESS_UNRESOLVED",
            "currentness_status": draft["controlled_currentness_status"],
            "supersession_status": draft["controlled_supersession_status"],
            "allowed_decision_types": [],
            "allowed_actions": [],
            "limitations": draft["review_issues"],
            "exclusions": [
                "Do not treat this record as proof that the cited provision is current law.",
                "Do not use this record to determine legal applicability, compliance, non-compliance, approval, notification, exemption, classification, or a prescribed pathway.",
                "Do not curate or activate this claim while currentness remains unresolved.",
            ],
            "reviewer_identity": reviewer_identity,
            "reviewer_role": reviewer_role,
            "review_date": review_date,
            "findings": [
                "The controlled base-instrument evidence and recorded currentness/supersession metadata were reviewed. The claim is dispositioned CURRENTNESS_UNRESOLVED and is not approved for the curated candidate claim set.",
                *draft["currentness_blockers"],
            ],
        })
        review["check_results"] = {key: "PASS" for key in review["check_results"]}
        review["attestations"] = {key: True for key in review["attestations"]}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply the project owner's CURRENTNESS_UNRESOLVED review to the nine legal claims."
    )
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--legal-draft", required=True, type=Path)
    parser.add_argument("--reviewer-identity", required=True)
    parser.add_argument("--reviewer-role", required=True)
    parser.add_argument("--review-date", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = apply_review(
        json.loads(args.review_map.read_text(encoding="utf-8")),
        json.loads(args.legal_draft.read_text(encoding="utf-8")),
        reviewer_identity=args.reviewer_identity,
        reviewer_role=args.reviewer_role,
        review_date=args.review_date,
    )
    write_json_atomic(result, args.output)
    completed = sum(item["review_status"] == CLAIM_REVIEW_COMPLETE for item in result["claim_reviews"])
    print(f"completed_claim_reviews={completed} legal_currentness_unresolved={len(LEGAL_CLAIM_IDS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())