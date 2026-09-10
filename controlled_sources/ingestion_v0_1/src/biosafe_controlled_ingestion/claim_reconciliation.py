from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


CROSSWALK_VERSION = "BioSafe_Document_Identity_Crosswalk_v0.1"
RECONCILIATION_MAP_VERSION = "BioSafe_Claim_Reconciliation_Map_v0.1"
RECONCILIATION_PACKET_VERSION = "BioSafe_Claim_Reconciliation_Packet_v0.1"
CURATED_KB_VERSION = "BioSafe_Curated_Candidate_KB_v0.1"

IDENTIFIER_MATCH_VALIDATED = "IDENTIFIER_MATCH_VALIDATED"
HUMAN_IDENTITY_REVIEW_REQUIRED = "HUMAN_IDENTITY_REVIEW_REQUIRED"
HUMAN_IDENTITY_REVIEW_COMPLETE = "HUMAN_IDENTITY_REVIEW_COMPLETE"
CLAIM_REVIEW_COMPLETE = "CLAIM_REVIEW_COMPLETE"

ALLOWED_RELATIONSHIPS = {
    "SAME_PROJECT_IDENTIFIER",
    "SAME_SOURCE_IDENTITY_DIFFERENT_PROJECT_IDENTIFIER",
}
ALLOWED_DISPOSITIONS = {
    "SUPPORTED_EXACTLY",
    "SUPPORTED_AFTER_ATOMIC_SPLIT",
    "PARTIALLY_SUPPORTED",
    "CONFLICTING_EVIDENCE",
    "INSUFFICIENT_EVIDENCE",
    "CURRENTNESS_UNRESOLVED",
}
CURATABLE_DISPOSITIONS = {
    "SUPPORTED_EXACTLY",
    "SUPPORTED_AFTER_ATOMIC_SPLIT",
}
ALLOWED_SUPPORT_KINDS = {"NATIVE_CANDIDATE", "REVIEWED_FALLBACK"}
ALLOWED_SUPPORT_TYPES = {"DIRECT", "CONTEXT", "LIMITATION"}
REQUIRED_CHECKS = {
    "exact_support_adequate",
    "atomicity_checked",
    "authority_and_jurisdiction_checked",
    "currentness_and_supersession_checked",
    "allowed_actions_checked",
    "limitations_and_exclusions_checked",
}
REQUIRED_ATTESTATIONS = {
    "controlled_source_compared",
    "historical_verification_not_relied_on",
    "not_live_activation_acknowledged",
}


def _require_text(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")


def _require_sha256(name: str, value: Any) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise ValidationError(f"{name} must be a lowercase SHA-256 digest")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_hashes(component_artifact: dict[str, Any]) -> dict[str, str]:
    hashes: dict[str, set[str]] = {}
    for chunk in component_artifact.get("candidate_chunks", []):
        hashes.setdefault(chunk["document_id"], set()).add(chunk["source_sha256"])
    if any(len(values) != 1 for values in hashes.values()):
        raise ValidationError("each controlled document must have exactly one source hash")
    return {document_id: next(iter(values)) for document_id, values in hashes.items()}


def validate_identity_crosswalk(
    crosswalk: dict[str, Any],
    knowledge_base: dict[str, Any],
    component_artifact: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if crosswalk.get("crosswalk_version") != CROSSWALK_VERSION:
        raise ValidationError("document identity crosswalk version is invalid")
    if crosswalk.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("document identity crosswalk must prohibit live activation")
    if crosswalk.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("document identity crosswalk must require claim review")
    source_hashes = _source_hashes(component_artifact)
    claim_document_ids = {claim["document_id"] for claim in knowledge_base.get("claims", [])}
    records = crosswalk.get("document_mappings")
    if not isinstance(records, list):
        raise ValidationError("document identity crosswalk mappings must be a list")
    mappings: dict[str, dict[str, Any]] = {}
    for record in records:
        legacy_id = record.get("legacy_document_id")
        controlled_id = record.get("controlled_document_id")
        _require_text("legacy document ID", legacy_id)
        _require_text("controlled document ID", controlled_id)
        if legacy_id in mappings:
            raise ValidationError(f"duplicate legacy document mapping: {legacy_id}")
        relationship = record.get("relationship")
        if relationship not in ALLOWED_RELATIONSHIPS:
            raise ValidationError(f"invalid document identity relationship for {legacy_id}")
        if relationship == "SAME_PROJECT_IDENTIFIER" and legacy_id != controlled_id:
            raise ValidationError("same-project-identifier mapping IDs must match")
        if relationship == "SAME_SOURCE_IDENTITY_DIFFERENT_PROJECT_IDENTIFIER" and legacy_id == controlled_id:
            raise ValidationError("different-project-identifier mapping IDs must differ")
        status = record.get("identity_review_status")
        review = record.get("identity_review_record")
        if not isinstance(review, dict):
            raise ValidationError("document identity mapping must contain an identity review record")
        if legacy_id == controlled_id:
            if status != IDENTIFIER_MATCH_VALIDATED:
                raise ValidationError(f"same-ID mapping status is invalid for {legacy_id}")
            if any(review.get(field) is not None for field in ("reviewer_identity", "reviewer_role", "review_date")):
                raise ValidationError("same-ID mapping must not invent a human identity review")
            if review.get("findings") != []:
                raise ValidationError("same-ID mapping findings must be empty")
        elif status == HUMAN_IDENTITY_REVIEW_REQUIRED:
            if any(review.get(field) is not None for field in ("reviewer_identity", "reviewer_role", "review_date")):
                raise ValidationError("pending identity review fields must be null")
            if review.get("findings") != []:
                raise ValidationError("pending identity review findings must be empty")
        elif status == HUMAN_IDENTITY_REVIEW_COMPLETE:
            for field in ("reviewer_identity", "reviewer_role", "review_date"):
                _require_text(f"identity review {field}", review.get(field))
            try:
                date.fromisoformat(review["review_date"])
            except (TypeError, ValueError) as error:
                raise ValidationError("identity review date must be an ISO calendar date") from error
            findings = review.get("findings")
            if not isinstance(findings, list) or not findings:
                raise ValidationError("completed identity review must record findings")
            for finding in findings:
                _require_text("identity review finding", finding)
        else:
            raise ValidationError(f"identity review status fails closed for {legacy_id}")
        if controlled_id not in source_hashes:
            raise ValidationError(f"controlled document is absent from candidate artifact: {controlled_id}")
        _require_sha256("crosswalk source SHA-256", record.get("source_sha256"))
        if record["source_sha256"] != source_hashes[controlled_id]:
            raise ValidationError(f"crosswalk source hash mismatch for {legacy_id}")
        _require_text("identity mapping rationale", record.get("rationale"))
        mappings[legacy_id] = record
    if set(mappings) != claim_document_ids:
        raise ValidationError("document identity crosswalk must cover the exact claim document set")
    return mappings


def initialize_claim_reconciliation_map(
    crosswalk: dict[str, Any],
    crosswalk_bytes: bytes,
    knowledge_base: dict[str, Any],
    knowledge_base_bytes: bytes,
    component_artifact: dict[str, Any],
    component_artifact_bytes: bytes,
    fallback_artifact_bytes: bytes,
    fallback_review_packet_bytes: bytes,
) -> dict[str, Any]:
    mappings = validate_identity_crosswalk(crosswalk, knowledge_base, component_artifact)
    reviews = []
    for claim in knowledge_base.get("claims", []):
        mapping = mappings[claim["document_id"]]
        reviews.append({
            "claim_id": claim["claim_id"],
            "original_claim": claim,
            "legacy_document_id": claim["document_id"],
            "controlled_document_id": mapping["controlled_document_id"],
            "controlled_source_sha256": mapping["source_sha256"],
            "identity_review_status": mapping["identity_review_status"],
            "review_status": CLAIM_REVIEW_REQUIRED,
            "disposition": None,
            "atomic_propositions": [],
            "support_spans": [],
            "authority_tier": None,
            "jurisdiction": None,
            "evidence_role": None,
            "currentness_status": None,
            "supersession_status": None,
            "allowed_decision_types": [],
            "allowed_actions": [],
            "limitations": [],
            "exclusions": [],
            "reviewer_identity": None,
            "reviewer_role": None,
            "review_date": None,
            "findings": [],
            "check_results": {check: None for check in sorted(REQUIRED_CHECKS)},
            "attestations": {attestation: False for attestation in sorted(REQUIRED_ATTESTATIONS)},
        })
    return {
        "reconciliation_map_version": RECONCILIATION_MAP_VERSION,
        "source_document_identity_crosswalk_sha256": _sha256(crosswalk_bytes),
        "source_knowledge_base_sha256": _sha256(knowledge_base_bytes),
        "source_component_artifact_sha256": _sha256(component_artifact_bytes),
        "source_fallback_artifact_sha256": _sha256(fallback_artifact_bytes),
        "source_fallback_review_packet_sha256": _sha256(fallback_review_packet_bytes),
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "live_activation_status": ACTIVATION_PROHIBITED,
        "claim_reviews": sorted(reviews, key=lambda item: item["claim_id"]),
    }


def _validate_pending(review: dict[str, Any]) -> None:
    null_fields = (
        "disposition", "authority_tier", "jurisdiction", "evidence_role",
        "currentness_status", "supersession_status", "reviewer_identity",
        "reviewer_role", "review_date",
    )
    if any(review.get(field) is not None for field in null_fields):
        raise ValidationError("pending claim review decision fields must be null")
    empty_fields = (
        "atomic_propositions", "support_spans", "allowed_decision_types",
        "allowed_actions", "limitations", "exclusions", "findings",
    )
    if any(review.get(field) != [] for field in empty_fields):
        raise ValidationError("pending claim review evidence fields must be empty")
    checks = review.get("check_results")
    if not isinstance(checks, dict) or set(checks) != REQUIRED_CHECKS:
        raise ValidationError("claim review checks must contain exactly the required fields")
    if any(value is not None for value in checks.values()):
        raise ValidationError("pending claim review checks must be null")
    attestations = review.get("attestations")
    if not isinstance(attestations, dict) or set(attestations) != REQUIRED_ATTESTATIONS:
        raise ValidationError("claim review attestations must contain exactly the required fields")
    if any(value is not False for value in attestations.values()):
        raise ValidationError("pending claim review attestations must be false")


def _validate_support(
    support: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    fallbacks: dict[str, dict[str, Any]],
    controlled_document_id: str,
    controlled_source_sha256: str,
    proposition_count: int,
    accepted_fallback_ids: set[str],
) -> None:
    kind = support.get("source_kind")
    if kind not in ALLOWED_SUPPORT_KINDS:
        raise ValidationError("claim support source kind is invalid")
    if support.get("support_type") not in ALLOWED_SUPPORT_TYPES:
        raise ValidationError("claim support type is invalid")
    _require_text("support record ID", support.get("source_record_id"))
    _require_text("quoted support", support.get("quoted_support"))
    proposition_indexes = support.get("atomic_proposition_indexes")
    if not isinstance(proposition_indexes, list) or not proposition_indexes:
        raise ValidationError("claim support must identify atomic proposition indexes")
    if any(
        not isinstance(index, int) or isinstance(index, bool) or index < 1 or index > proposition_count
        for index in proposition_indexes
    ) or len(proposition_indexes) != len(set(proposition_indexes)):
        raise ValidationError("claim support atomic proposition indexes are invalid")
    records = candidates if kind == "NATIVE_CANDIDATE" else fallbacks
    record = records.get(support["source_record_id"])
    if record is None:
        raise ValidationError("claim support record does not exist")
    if record["document_id"] != controlled_document_id:
        raise ValidationError("claim support document does not match controlled identity")
    if record["source_sha256"] != controlled_source_sha256:
        raise ValidationError("claim support source hash mismatch")
    page_start = support.get("pdf_page_start")
    page_end = support.get("pdf_page_end")
    if not isinstance(page_start, int) or not isinstance(page_end, int) or page_start < 1 or page_end < page_start:
        raise ValidationError("claim support PDF page range is invalid")
    if kind == "NATIVE_CANDIDATE":
        if page_start != record["pdf_page_start"] or page_end != record["pdf_page_end"]:
            raise ValidationError("native claim support page range must match its candidate")
        if support["quoted_support"] not in record["text"]:
            raise ValidationError("quoted native support must occur exactly in candidate text")
    else:
        if support["source_record_id"] not in accepted_fallback_ids:
            raise ValidationError("fallback claim support does not have accepted unit-level review")
        if page_start != record["pdf_page_index"] or page_end != record["pdf_page_index"]:
            raise ValidationError("fallback claim support page must match its fallback unit")
        representation_text = json.dumps(record["structured_representation"], ensure_ascii=False)
        if support["quoted_support"] not in representation_text:
            raise ValidationError("quoted fallback support must occur in the structured representation")


def _validate_complete(
    review: dict[str, Any],
    candidates: dict[str, dict[str, Any]],
    fallbacks: dict[str, dict[str, Any]],
    accepted_fallback_ids: set[str],
) -> None:
    if review.get("identity_review_status") == HUMAN_IDENTITY_REVIEW_REQUIRED:
        raise ValidationError("claim review cannot complete while document identity review is pending")
    if review.get("disposition") not in ALLOWED_DISPOSITIONS:
        raise ValidationError("completed claim review disposition is invalid")
    for field in (
        "authority_tier", "jurisdiction", "evidence_role", "currentness_status",
        "supersession_status", "reviewer_identity", "reviewer_role", "review_date",
    ):
        _require_text(f"completed claim review {field}", review.get(field))
    try:
        date.fromisoformat(review["review_date"])
    except (TypeError, ValueError) as error:
        raise ValidationError("claim review date must be an ISO calendar date") from error
    for field in ("atomic_propositions", "findings", "limitations", "exclusions"):
        values = review.get(field)
        if not isinstance(values, list) or not values:
            raise ValidationError(f"completed claim review {field} must not be empty")
        for value in values:
            _require_text(f"completed claim review {field} item", value)
    for field in ("allowed_decision_types", "allowed_actions"):
        values = review.get(field)
        if not isinstance(values, list):
            raise ValidationError(f"completed claim review {field} must be a list")
        for value in values:
            _require_text(f"completed claim review {field} item", value)
    supports = review.get("support_spans")
    if not isinstance(supports, list):
        raise ValidationError("completed claim review support spans must be a list")
    if review["disposition"] in CURATABLE_DISPOSITIONS and not supports:
        raise ValidationError("supported claim review must include exact support spans")
    for support in supports:
        _validate_support(
            support, candidates, fallbacks, review["controlled_document_id"],
            review["controlled_source_sha256"], len(review["atomic_propositions"]),
            accepted_fallback_ids,
        )
    if review["disposition"] in CURATABLE_DISPOSITIONS:
        directly_supported = {
            index
            for support in supports
            if support["support_type"] == "DIRECT"
            for index in support["atomic_proposition_indexes"]
        }
        if directly_supported != set(range(1, len(review["atomic_propositions"]) + 1)):
            raise ValidationError("every atomic proposition requires direct exact support")
    checks = review.get("check_results")
    if not isinstance(checks, dict) or set(checks) != REQUIRED_CHECKS or set(checks.values()) != {"PASS"}:
        raise ValidationError("completed claim review requires every check to pass")
    attestations = review.get("attestations")
    if not isinstance(attestations, dict) or set(attestations) != REQUIRED_ATTESTATIONS or any(
        value is not True for value in attestations.values()
    ):
        raise ValidationError("completed claim review requires all attestations")


def build_claim_reconciliation_artifacts(
    crosswalk: dict[str, Any],
    crosswalk_bytes: bytes,
    reconciliation_map: dict[str, Any],
    knowledge_base: dict[str, Any],
    knowledge_base_bytes: bytes,
    component_artifact: dict[str, Any],
    component_artifact_bytes: bytes,
    fallback_artifact: dict[str, Any],
    fallback_artifact_bytes: bytes,
    fallback_review_packet: dict[str, Any],
    fallback_review_packet_bytes: bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if reconciliation_map.get("reconciliation_map_version") != RECONCILIATION_MAP_VERSION:
        raise ValidationError("claim reconciliation map version is invalid")
    if reconciliation_map.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("claim reconciliation map must require claim review")
    if reconciliation_map.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("claim reconciliation map must prohibit live activation")
    for name, artifact in (
        ("component artifact", component_artifact),
        ("fallback artifact", fallback_artifact),
        ("fallback review packet", fallback_review_packet),
    ):
        if artifact.get("live_activation_status") != ACTIVATION_PROHIBITED:
            raise ValidationError(f"{name} must prohibit live activation")
        if artifact.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
            raise ValidationError(f"{name} must require claim review")
    expected_hashes = {
        "source_document_identity_crosswalk_sha256": _sha256(crosswalk_bytes),
        "source_knowledge_base_sha256": _sha256(knowledge_base_bytes),
        "source_component_artifact_sha256": _sha256(component_artifact_bytes),
        "source_fallback_artifact_sha256": _sha256(fallback_artifact_bytes),
        "source_fallback_review_packet_sha256": _sha256(fallback_review_packet_bytes),
    }
    for field, expected in expected_hashes.items():
        if reconciliation_map.get(field) != expected:
            raise ValidationError(f"claim reconciliation provenance mismatch: {field}")
    if fallback_review_packet.get("review_gate_status") != "TRANSCRIPTION_REVIEW_ACCEPTED_CLAIM_REVIEW_REQUIRED":
        raise ValidationError("fallback transcription-review gate is not accepted")
    if fallback_review_packet.get("source_fallback_artifact_sha256") != _sha256(fallback_artifact_bytes):
        raise ValidationError("fallback review packet is not bound to the source fallback artifact")
    mappings = validate_identity_crosswalk(crosswalk, knowledge_base, component_artifact)
    claims = {claim["claim_id"]: claim for claim in knowledge_base.get("claims", [])}
    candidates = {
        item["candidate_chunk_id"]: item for item in component_artifact.get("candidate_chunks", [])
    }
    fallbacks = {
        item["fallback_unit_id"]: item for item in fallback_artifact.get("fallback_units", [])
    }
    accepted_fallback_ids = {
        item["fallback_unit_id"]
        for item in fallback_review_packet.get("review_items", [])
        if item.get("review_record", {}).get("review_status") == "HUMAN_REVIEW_COMPLETE"
        and item.get("review_record", {}).get("disposition") == "ACCEPT_AS_TRANSCRIBED"
    }
    if accepted_fallback_ids != set(fallbacks):
        raise ValidationError("fallback review packet must accept the exact fallback unit set")
    reviews = reconciliation_map.get("claim_reviews")
    if not isinstance(reviews, list):
        raise ValidationError("claim reviews must be a list")
    seen: set[str] = set()
    packet_items = []
    curated_claims = []
    for review in reviews:
        claim_id = review.get("claim_id")
        if claim_id in seen or claim_id not in claims:
            raise ValidationError("claim reconciliation must contain unique known claim IDs")
        seen.add(claim_id)
        claim = claims[claim_id]
        if review.get("original_claim") != claim:
            raise ValidationError(f"original claim snapshot mismatch for {claim_id}")
        mapping = mappings[claim["document_id"]]
        for field, expected in (
            ("legacy_document_id", claim["document_id"]),
            ("controlled_document_id", mapping["controlled_document_id"]),
            ("controlled_source_sha256", mapping["source_sha256"]),
            ("identity_review_status", mapping["identity_review_status"]),
        ):
            if review.get(field) != expected:
                raise ValidationError(f"claim identity binding mismatch for {claim_id}: {field}")
        status = review.get("review_status")
        if status == CLAIM_REVIEW_REQUIRED:
            _validate_pending(review)
        elif status == CLAIM_REVIEW_COMPLETE:
            _validate_complete(review, candidates, fallbacks, accepted_fallback_ids)
        else:
            raise ValidationError("claim review status is invalid")
        packet_items.append(review)
        if status == CLAIM_REVIEW_COMPLETE and review["disposition"] in CURATABLE_DISPOSITIONS:
            curated_claims.append(review)
    if seen != set(claims):
        raise ValidationError("claim reconciliation map must cover the exact knowledge-base claim set")
    complete_count = sum(item["review_status"] == CLAIM_REVIEW_COMPLETE for item in packet_items)
    packet = {
        "review_packet_version": RECONCILIATION_PACKET_VERSION,
        **expected_hashes,
        "review_scope": "CLAIM_TO_CONTROLLED_SOURCE_RECONCILIATION_ONLY",
        "review_completion_status": (
            "CLAIM_REVIEW_COMPLETE" if complete_count == len(packet_items) else CLAIM_REVIEW_REQUIRED
        ),
        "completed_review_count": complete_count,
        "required_review_count": len(packet_items),
        "curated_claim_count": len(curated_claims),
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "live_activation_status": ACTIVATION_PROHIBITED,
        "review_items": sorted(packet_items, key=lambda item: item["claim_id"]),
    }
    curated = {
        "artifact_version": CURATED_KB_VERSION,
        **expected_hashes,
        "source_reconciliation_packet_version": RECONCILIATION_PACKET_VERSION,
        "artifact_scope": "ADDITIVE_OFFLINE_CURATED_CANDIDATE_REFERENCE_ONLY",
        "curated_claim_count": len(curated_claims),
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "live_activation_status": ACTIVATION_PROHIBITED,
        "curated_claims": sorted(curated_claims, key=lambda item: item["claim_id"]),
    }
    return packet, curated


def write_json_atomic(payload: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, output)