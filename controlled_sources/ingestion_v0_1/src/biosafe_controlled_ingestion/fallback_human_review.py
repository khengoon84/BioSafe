from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


REVIEW_MAP_VERSION = "BioSafe_Fallback_Human_Review_Map_v0.1"
REVIEW_PACKET_VERSION = "BioSafe_Fallback_Human_Review_Packet_v0.1"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
HUMAN_REVIEW_COMPLETE = "HUMAN_REVIEW_COMPLETE"
ALLOWED_DISPOSITIONS = {
    "ACCEPT_AS_TRANSCRIBED",
    "CORRECTION_REQUIRED",
    "REJECT_REPRESENTATION",
    "UNRESOLVED_SOURCE_AMBIGUITY",
}
ALLOWED_CHECK_RESULTS = {"PASS", "FAIL", "AMBIGUOUS"}
ATTESTATION_FIELDS = {
    "source_render_compared",
    "representation_checked",
    "not_claim_approval_acknowledged",
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


def _validate_pending_review(review: dict[str, Any], check_ids: set[str]) -> None:
    if review.get("disposition") is not None:
        raise ValidationError("pending human review disposition must be null")
    for field in ("reviewer_identity", "reviewer_role", "review_date"):
        if review.get(field) is not None:
            raise ValidationError(f"pending human review {field} must be null")
    if review.get("findings") != []:
        raise ValidationError("pending human review findings must be empty")
    results = review.get("check_results")
    if not isinstance(results, dict) or set(results) != check_ids:
        raise ValidationError("human review results must cover exactly the required checks")
    if any(value is not None for value in results.values()):
        raise ValidationError("pending human review check results must be null")
    attestations = review.get("attestations")
    if not isinstance(attestations, dict) or set(attestations) != ATTESTATION_FIELDS:
        raise ValidationError("human review attestations must contain exactly the required fields")
    if any(value is not False for value in attestations.values()):
        raise ValidationError("pending human review attestations must be false")


def _validate_completed_review(review: dict[str, Any], check_ids: set[str]) -> None:
    disposition = review.get("disposition")
    if disposition not in ALLOWED_DISPOSITIONS:
        raise ValidationError("completed human review disposition is invalid")
    for field in ("reviewer_identity", "reviewer_role", "review_date"):
        _require_text(f"human review {field}", review.get(field))
    try:
        date.fromisoformat(review["review_date"])
    except (TypeError, ValueError) as error:
        raise ValidationError("human review date must be an ISO calendar date") from error
    findings = review.get("findings")
    if not isinstance(findings, list) or not findings:
        raise ValidationError("completed human review must record findings")
    for finding in findings:
        _require_text("human review finding", finding)
    results = review.get("check_results")
    if not isinstance(results, dict) or set(results) != check_ids:
        raise ValidationError("human review results must cover exactly the required checks")
    if any(value not in ALLOWED_CHECK_RESULTS for value in results.values()):
        raise ValidationError("completed human review contains an invalid check result")
    attestations = review.get("attestations")
    if not isinstance(attestations, dict) or set(attestations) != ATTESTATION_FIELDS:
        raise ValidationError("human review attestations must contain exactly the required fields")
    if any(value is not True for value in attestations.values()):
        raise ValidationError("completed human review requires all attestations")
    values = set(results.values())
    if disposition == "ACCEPT_AS_TRANSCRIBED" and values != {"PASS"}:
        raise ValidationError("acceptance requires every human review check to pass")
    if disposition in {"CORRECTION_REQUIRED", "REJECT_REPRESENTATION"} and "FAIL" not in values:
        raise ValidationError("correction or rejection requires a failed check")
    if disposition == "UNRESOLVED_SOURCE_AMBIGUITY" and "AMBIGUOUS" not in values:
        raise ValidationError("unresolved ambiguity requires an ambiguous check")


def _validate_review(review: dict[str, Any], check_ids: set[str]) -> None:
    status = review.get("review_status")
    if status == HUMAN_REVIEW_REQUIRED:
        _validate_pending_review(review, check_ids)
    elif status == HUMAN_REVIEW_COMPLETE:
        _validate_completed_review(review, check_ids)
    else:
        raise ValidationError("human review status is invalid")


def build_fallback_human_review_packet(
    review_map: dict[str, Any],
    fallback_artifact: dict[str, Any],
    fallback_artifact_bytes: bytes,
    render_manifest: dict[str, Any],
) -> dict[str, Any]:
    if review_map.get("review_map_version") != REVIEW_MAP_VERSION:
        raise ValidationError("unsupported fallback human-review map version")
    if review_map.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("human-review packet must remain claim-review-gated")
    if review_map.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("human-review packet must prohibit live activation")
    try:
        artifact_from_bytes = json.loads(fallback_artifact_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError("source fallback artifact bytes must contain valid JSON") from error
    if artifact_from_bytes != fallback_artifact:
        raise ValidationError("parsed fallback artifact does not match hash-bound bytes")
    if fallback_artifact.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("source fallback artifact must remain claim-review-gated")
    if fallback_artifact.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("source fallback artifact must prohibit live activation")
    observed_artifact_hash = hashlib.sha256(fallback_artifact_bytes).hexdigest()
    _require_sha256("source fallback artifact hash", review_map.get("source_fallback_artifact_sha256"))
    if review_map["source_fallback_artifact_sha256"] != observed_artifact_hash:
        raise ValidationError("source fallback artifact hash does not match canonical bytes")

    fallback_units = {
        unit["fallback_unit_id"]: unit for unit in fallback_artifact.get("fallback_units", [])
    }
    renders = {
        (item["document_id"], int(item["pdf_page_index"])): item
        for item in render_manifest.get("renders", [])
    }
    raw_items = review_map.get("review_items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValidationError("human-review map must contain review items")
    if len(raw_items) != len(fallback_units):
        raise ValidationError("human-review map must cover every fallback unit exactly once")

    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    for raw in raw_items:
        unit_id = raw.get("fallback_unit_id")
        _require_text("fallback unit ID", unit_id)
        if unit_id in seen:
            raise ValidationError("human-review fallback unit IDs must be unique")
        seen.add(unit_id)
        unit = fallback_units.get(unit_id)
        if unit is None:
            raise ValidationError("human-review item references an unknown fallback unit")
        if unit.get("human_review_status") != HUMAN_REVIEW_REQUIRED:
            raise ValidationError("source fallback unit must remain human-review-required")
        render = renders.get((unit["document_id"], int(unit["pdf_page_index"])))
        if render is None or any(
            render.get(field) != unit.get(unit_field)
            for field, unit_field in (
                ("source_sha256", "source_sha256"),
                ("rendered_filename", "rendered_filename"),
                ("rendered_sha256", "render_sha256"),
            )
        ):
            raise ValidationError("human-review item render provenance does not match")

        checks = raw.get("required_checks")
        if not isinstance(checks, list) or not checks:
            raise ValidationError("human-review item must define required checks")
        check_ids: list[str] = []
        for check in checks:
            _require_text("human-review check ID", check.get("check_id"))
            _require_text("human-review check prompt", check.get("prompt"))
            check_ids.append(check["check_id"])
        if len(check_ids) != len(set(check_ids)):
            raise ValidationError("human-review check IDs must be unique within an item")
        review = raw.get("review_record")
        if not isinstance(review, dict):
            raise ValidationError("human-review item must contain a review record")
        _validate_review(review, set(check_ids))

        items.append({
            "fallback_unit_id": unit_id,
            "document_id": unit["document_id"],
            "component_id": unit["component_id"],
            "source_sha256": unit["source_sha256"],
            "pdf_page_index": unit["pdf_page_index"],
            "pdf_page_label": unit["pdf_page_label"],
            "printed_page_label": unit.get("printed_page_label", ""),
            "rendered_filename": unit["rendered_filename"],
            "render_sha256": unit["render_sha256"],
            "representation_type": unit["structured_representation"]["representation_type"],
            "structured_representation": unit["structured_representation"],
            "limitations": unit["limitations"],
            "required_checks": checks,
            "review_record": review,
            "claim_use_status": CLAIM_REVIEW_REQUIRED,
            "live_activation_status": ACTIVATION_PROHIBITED,
        })

    if seen != set(fallback_units):
        raise ValidationError("human-review map does not cover the exact fallback unit set")
    completed = sum(
        item["review_record"]["review_status"] == HUMAN_REVIEW_COMPLETE for item in items
    )
    dispositions = {
        item["review_record"]["disposition"]
        for item in items
        if item["review_record"]["review_status"] == HUMAN_REVIEW_COMPLETE
    }
    if completed != len(items):
        gate_status = "BLOCKED_HUMAN_REVIEW_REQUIRED"
    elif "REJECT_REPRESENTATION" in dispositions:
        gate_status = "BLOCKED_REPRESENTATION_REJECTED"
    elif "CORRECTION_REQUIRED" in dispositions:
        gate_status = "BLOCKED_CORRECTION_REQUIRED"
    elif "UNRESOLVED_SOURCE_AMBIGUITY" in dispositions:
        gate_status = "BLOCKED_UNRESOLVED_SOURCE_AMBIGUITY"
    else:
        gate_status = "TRANSCRIPTION_REVIEW_ACCEPTED_CLAIM_REVIEW_REQUIRED"
    return {
        "review_packet_version": REVIEW_PACKET_VERSION,
        "source_fallback_artifact_version": fallback_artifact.get("artifact_version", ""),
        "source_fallback_artifact_sha256": observed_artifact_hash,
        "review_scope": "TRANSCRIPTION_AND_REPRESENTATION_ONLY",
        "review_completion_status": (
            "HUMAN_REVIEW_COMPLETE" if completed == len(items) else "HUMAN_REVIEW_REQUIRED"
        ),
        "review_gate_status": gate_status,
        "completed_review_count": completed,
        "required_review_count": len(items),
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "live_activation_status": ACTIVATION_PROHIBITED,
        "review_items": sorted(items, key=lambda item: item["fallback_unit_id"]),
    }


def write_fallback_human_review_packet(packet: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, output)