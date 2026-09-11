from __future__ import annotations

from typing import Any

from .claim_decision_entry import (
    DECISION_FIELDS,
    DECISION_PACKET_VERSION,
    HUMAN_REVIEW_REQUIRED,
    sha256,
)
from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


WORKSHEET_VERSION = "BioSafe_Claim_Review_Pilot_Worksheet_v0.1"


def initialize_decision_template(
    review_map: dict[str, Any],
    review_map_bytes: bytes,
    review_aid: dict[str, Any],
    review_aid_bytes: bytes,
    claim_ids: list[str],
    batch_id: str,
) -> tuple[dict[str, Any], str]:
    if not batch_id.strip():
        raise ValidationError("batch_id must not be empty")
    if claim_ids != sorted(claim_ids) or len(claim_ids) != len(set(claim_ids)) or not claim_ids:
        raise ValidationError("claim IDs must be a non-empty sorted unique list")
    if review_aid.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("review aid must require claim review")
    if review_aid.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("review aid must prohibit live activation")
    if review_aid.get("source_claim_reconciliation_map_sha256") != sha256(review_map_bytes):
        raise ValidationError("review aid is not bound to supplied review map")

    reviews = {item["claim_id"]: item for item in review_map.get("claim_reviews", [])}
    aid_items = {item["claim_id"]: item for item in review_aid.get("claim_review_items", [])}
    decisions = []
    worksheet = [
        f"# Human claim-review worksheet — {batch_id}", "",
        f"Version: `{WORKSHEET_VERSION}`.", "",
        "**Status: HUMAN REVIEW REQUIRED. No decision has been made by this template.**", "",
        f"Canonical map SHA-256: `{sha256(review_map_bytes)}`.",
        f"Review aid SHA-256: `{sha256(review_aid_bytes)}`.", "",
        "For each claim, compare the immutable staged PDF with the cited candidate text. "
        "Do not treat a navigation suggestion as support. Record the completed human decision "
        "in the JSON template; then set top-level `human_review_status` to "
        "`HUMAN_REVIEW_COMPLETE` only after every field, check, and attestation is complete.", "",
    ]
    for claim_id in claim_ids:
        if claim_id not in reviews or claim_id not in aid_items:
            raise ValidationError(f"pilot claim is missing: {claim_id}")
        review = reviews[claim_id]
        aid = aid_items[claim_id]
        if review.get("review_status") != CLAIM_REVIEW_REQUIRED:
            raise ValidationError(f"pilot claim is not pending: {claim_id}")
        if aid.get("claim_review_status") != CLAIM_REVIEW_REQUIRED:
            raise ValidationError(f"review aid claim is not pending: {claim_id}")
        decision = {"claim_id": claim_id}
        decision.update({field: review[field] for field in DECISION_FIELDS})
        decisions.append(decision)
        candidates = [item["candidate_chunk_id"] for item in aid["native_candidate_suggestions"]]
        fallbacks = [item["fallback_unit_id"] for item in aid["reviewed_fallback_suggestions"]]
        worksheet.extend([
            f"## {claim_id}", "",
            f"Original claim: {review['original_claim']['text']}", "",
            f"Controlled document: `{review['controlled_document_id']}`",
            f"Controlled source SHA-256: `{review['controlled_source_sha256']}`",
            "Candidate navigation IDs: " + (
                ", ".join(f"`{value}`" for value in candidates) if candidates else "none"
            ),
            "Accepted fallback navigation IDs: " + (
                ", ".join(f"`{value}`" for value in fallbacks) if fallbacks else "none"
            ), "",
            "Required boundary prompts:",
            *[f"- {prompt}" for prompt in aid["boundary_prompts"]], "",
            "Reviewer checklist:",
            "- [ ] Compared immutable staged PDF and source-bound candidate text",
            "- [ ] Atomized the claim without adding unsupported meaning",
            "- [ ] Recorded exact quote/page/source IDs for every supported proposition",
            "- [ ] Recorded authority, jurisdiction, currentness, and supersession",
            "- [ ] Recorded allowed decisions/actions, limitations, and exclusions",
            "- [ ] Recorded reviewer identity, role, ISO date, and findings",
            "- [ ] Set all required checks to `PASS` and attestations to `true`",
            "- [ ] Confirmed every claim-specific boundary prompt above was preserved", "",
        ])

    packet = {
        "decision_packet_version": DECISION_PACKET_VERSION,
        "human_review_status": HUMAN_REVIEW_REQUIRED,
        "batch_id": batch_id,
        "source_review_map_sha256": sha256(review_map_bytes),
        "source_review_aid_sha256": sha256(review_aid_bytes),
        "claim_ids": claim_ids,
        "decisions": decisions,
    }
    return packet, "\n".join(worksheet).rstrip() + "\n"