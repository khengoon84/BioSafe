from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .claim_reconciliation import validate_identity_crosswalk, write_json_atomic
from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


REVIEW_AID_VERSION = "BioSafe_Claim_Reconciliation_Review_Aid_v0.1"
NO_AUTOMATED_DISPOSITION = "NAVIGATION_AID_ONLY_NO_AUTOMATED_DISPOSITION"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _page_hint(value: str) -> tuple[int, int] | None:
    patterns = (
        r"^(\d+)[–-](\d+)$",
        r"^pp?\.\s*(\d+)[–-](\d+)",
        r"^Form E pp?\.\s*(\d+)[–-](\d+)",
        r"^Form E pp?\.\s*(\d+)\b",
    )
    for pattern in patterns:
        match = re.match(pattern, value, flags=re.IGNORECASE)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.lastindex == 2 else start
            return start, end
    return None


def _boundary_prompts(document_id: str) -> list[str]:
    prompts = [
        "A navigation suggestion is not claim support or a review disposition.",
        "Unknown, conflicting, or currentness-unresolved information must remain unresolved.",
    ]
    if document_id.startswith("KB-WHO-"):
        prompts.append("WHO material is international guidance, not Malaysian law or regulatory proof.")
    if document_id == "KB-MY-FORME":
        prompts.append("Form E is not an approval, submission, permit, or regulatory determination.")
    if document_id == "KB-MY-SW2005":
        prompts.append("Biological material or biological waste is not automatically SW 404.")
    if document_id == "KB-MY-TRANSPORT2023":
        prompts.append("Transport guidance does not establish laboratory containment or clinical-waste requirements.")
    if document_id in {"KB-MY-CU", "KB-MY-GMMRA"}:
        prompts.append("Risk group, organism hazard, procedure-specific risk, and containment level remain distinct.")
    return prompts


def build_claim_review_aid(
    crosswalk: dict[str, Any],
    crosswalk_bytes: bytes,
    reconciliation_map: dict[str, Any],
    reconciliation_map_bytes: bytes,
    knowledge_base: dict[str, Any],
    knowledge_base_bytes: bytes,
    source_policy: dict[str, Any],
    source_policy_bytes: bytes,
    source_register: list[dict[str, str]],
    source_register_bytes: bytes,
    component_artifact: dict[str, Any],
    component_artifact_bytes: bytes,
    fallback_artifact: dict[str, Any],
    fallback_artifact_bytes: bytes,
    fallback_review_packet: dict[str, Any],
    fallback_review_packet_bytes: bytes,
) -> dict[str, Any]:
    for name, artifact in (
        ("component artifact", component_artifact),
        ("fallback artifact", fallback_artifact),
        ("fallback review packet", fallback_review_packet),
    ):
        if artifact.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
            raise ValidationError(f"{name} must require claim review")
        if artifact.get("live_activation_status") != ACTIVATION_PROHIBITED:
            raise ValidationError(f"{name} must prohibit live activation")
    if reconciliation_map.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("claim reconciliation map must require claim review")
    if reconciliation_map.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("claim reconciliation map must prohibit live activation")

    mappings = validate_identity_crosswalk(crosswalk, knowledge_base, component_artifact)
    expected_hashes = {
        "source_document_identity_crosswalk_sha256": _sha256(crosswalk_bytes),
        "source_claim_reconciliation_map_sha256": _sha256(reconciliation_map_bytes),
        "source_knowledge_base_sha256": _sha256(knowledge_base_bytes),
        "source_policy_sha256": _sha256(source_policy_bytes),
        "source_register_sha256": _sha256(source_register_bytes),
        "source_component_artifact_sha256": _sha256(component_artifact_bytes),
        "source_fallback_artifact_sha256": _sha256(fallback_artifact_bytes),
        "source_fallback_review_packet_sha256": _sha256(fallback_review_packet_bytes),
    }
    for field in (
        "source_document_identity_crosswalk_sha256", "source_knowledge_base_sha256",
        "source_component_artifact_sha256", "source_fallback_artifact_sha256",
        "source_fallback_review_packet_sha256",
    ):
        if reconciliation_map.get(field) != expected_hashes[field]:
            raise ValidationError(f"review-aid provenance mismatch: {field}")

    policies = source_policy.get("sources", {})
    register_by_id: dict[str, dict[str, str]] = {}
    for record in source_register:
        document_id = record.get("candidate_id", "")
        if not document_id or document_id in register_by_id:
            raise ValidationError("source register must contain unique non-empty candidate IDs")
        register_by_id[document_id] = record
    candidates_by_document: dict[str, list[dict[str, Any]]] = {}
    for candidate in component_artifact.get("candidate_chunks", []):
        candidates_by_document.setdefault(candidate["document_id"], []).append(candidate)
    components_by_document: dict[str, list[dict[str, Any]]] = {}
    for component in component_artifact.get("components", []):
        components_by_document.setdefault(component["document_id"], []).append(component)
    accepted_fallbacks: dict[str, set[str]] = {}
    for item in fallback_review_packet.get("review_items", []):
        review = item.get("review_record", {})
        if review.get("review_status") == "HUMAN_REVIEW_COMPLETE" and review.get("disposition") == "ACCEPT_AS_TRANSCRIBED":
            accepted_fallbacks.setdefault(item["document_id"], set()).add(item["fallback_unit_id"])
    fallbacks_by_document: dict[str, list[dict[str, Any]]] = {}
    for fallback in fallback_artifact.get("fallback_units", []):
        if fallback["fallback_unit_id"] in accepted_fallbacks.get(fallback["document_id"], set()):
            fallbacks_by_document.setdefault(fallback["document_id"], []).append(fallback)

    identity_items = []
    for legacy_id, mapping in sorted(mappings.items()):
        if legacy_id == mapping["controlled_document_id"]:
            continue
        controlled_id = mapping["controlled_document_id"]
        legacy = next(item for item in knowledge_base["documents"] if item["document_id"] == legacy_id)
        if controlled_id not in policies or controlled_id not in register_by_id:
            raise ValidationError(f"identity review source metadata is missing for {controlled_id}")
        register_record = register_by_id[controlled_id]
        if register_record.get("sha256") != mapping["source_sha256"]:
            raise ValidationError(f"identity review register hash mismatch for {controlled_id}")
        front_matter = sorted(
            candidates_by_document.get(controlled_id, []),
            key=lambda item: (item["pdf_page_start"], item["candidate_chunk_id"]),
        )[:3]
        identity_items.append({
            "legacy_document": legacy,
            "proposed_controlled_document_id": controlled_id,
            "controlled_source_sha256": mapping["source_sha256"],
            "controlled_source_metadata": policies[controlled_id],
            "controlled_source_register_record": register_record,
            "controlled_front_matter_candidates": [{
                "candidate_chunk_id": item["candidate_chunk_id"],
                "source_sha256": item["source_sha256"],
                "pdf_page_start": item["pdf_page_start"],
                "pdf_page_end": item["pdf_page_end"],
                "text": item["text"],
            } for item in front_matter],
            "mapping_rationale": mapping["rationale"],
            "identity_review_status": mapping["identity_review_status"],
            "identity_review_record": mapping["identity_review_record"],
            "review_instruction": "Compare official publication identity and front matter; do not accept from title similarity alone.",
            "automated_disposition": None,
        })

    claims = {claim["claim_id"]: claim for claim in knowledge_base.get("claims", [])}
    reconciliation_reviews = reconciliation_map.get("claim_reviews")
    if not isinstance(reconciliation_reviews, list):
        raise ValidationError("claim reconciliation map reviews must be a list")
    review_items = []
    seen: set[str] = set()
    for review in reconciliation_reviews:
        claim_id = review.get("claim_id")
        if claim_id in seen or claim_id not in claims:
            raise ValidationError("review aid requires unique known claim IDs")
        seen.add(claim_id)
        claim = review["original_claim"]
        if claim != claims[claim_id]:
            raise ValidationError(f"review-aid original claim mismatch for {claim_id}")
        controlled_id = review["controlled_document_id"]
        mapping = mappings[claim["document_id"]]
        for field, expected in (
            ("legacy_document_id", claim["document_id"]),
            ("controlled_document_id", mapping["controlled_document_id"]),
            ("controlled_source_sha256", mapping["source_sha256"]),
            ("identity_review_status", mapping["identity_review_status"]),
        ):
            if review.get(field) != expected:
                raise ValidationError(f"review-aid identity binding mismatch for {claim_id}: {field}")
        hint = _page_hint(str(claim.get("page", "")))
        native = []
        fallback = []
        excluded_pages: set[int] = set()
        component_navigation = []
        for component in components_by_document.get(controlled_id, []):
            component_navigation.append({
                "component_id": component["component_id"],
                "component_type": component["component_type"],
                "title": component["title"],
                "spans": component["spans"],
                "candidate_excluded_pages": component["candidate_excluded_pages"],
                "review_status": component["review_status"],
            })
            excluded_pages.update(component["candidate_excluded_pages"])
        if hint:
            start, end = hint
            for candidate in candidates_by_document.get(controlled_id, []):
                if start <= candidate["pdf_page_start"] <= end:
                    native.append({
                        "candidate_chunk_id": candidate["candidate_chunk_id"],
                        "component_id": candidate["component_id"],
                        "source_sha256": candidate["source_sha256"],
                        "pdf_page_start": candidate["pdf_page_start"],
                        "pdf_page_end": candidate["pdf_page_end"],
                        "text": candidate["text"],
                    })
            for item in fallbacks_by_document.get(controlled_id, []):
                if start <= item["pdf_page_index"] <= end:
                    fallback.append({
                        "fallback_unit_id": item["fallback_unit_id"],
                        "component_id": item["component_id"],
                        "source_sha256": item["source_sha256"],
                        "pdf_page_index": item["pdf_page_index"],
                        "structured_representation": item["structured_representation"],
                        "limitations": item["limitations"],
                    })
        review_items.append({
            "claim_id": claim_id,
            "original_claim": claim,
            "controlled_document_id": controlled_id,
            "controlled_source_sha256": review["controlled_source_sha256"],
            "identity_review_status": review["identity_review_status"],
            "claim_review_status": review["review_status"],
            "controlled_source_metadata": policies[controlled_id],
            "page_hint": (
                {"pdf_page_start": hint[0], "pdf_page_end": hint[1], "basis": "LEGACY_PAGE_FIELD_NAVIGATION_ONLY"}
                if hint else None
            ),
            "manual_navigation_required": hint is None,
            "native_candidate_suggestions": sorted(native, key=lambda item: item["candidate_chunk_id"]),
            "reviewed_fallback_suggestions": sorted(fallback, key=lambda item: item["fallback_unit_id"]),
            "excluded_native_pages_in_hint": (
                sorted(page for page in excluded_pages if hint[0] <= page <= hint[1]) if hint else []
            ),
            "component_navigation": sorted(component_navigation, key=lambda item: item["component_id"]),
            "boundary_prompts": _boundary_prompts(controlled_id),
            "automated_atomic_propositions": [],
            "automated_disposition": None,
            "reviewer_identity": None,
            "reviewer_attestations": None,
        })
    if seen != set(claims):
        raise ValidationError("review aid requires the exact knowledge-base claim set")

    return {
        "review_aid_version": REVIEW_AID_VERSION,
        **expected_hashes,
        "aid_scope": NO_AUTOMATED_DISPOSITION,
        "identity_mapping_item_count": len(identity_items),
        "completed_identity_review_count": sum(
            item["identity_review_status"] == "HUMAN_IDENTITY_REVIEW_COMPLETE"
            for item in identity_items
        ),
        "pending_identity_review_count": sum(
            item["identity_review_status"] == "HUMAN_IDENTITY_REVIEW_REQUIRED"
            for item in identity_items
        ),
        "claim_review_item_count": len(review_items),
        "completed_claim_review_count": sum(
            item["claim_review_status"] == "CLAIM_REVIEW_COMPLETE"
            for item in review_items
        ),
        "pending_claim_review_count": sum(
            item["claim_review_status"] == CLAIM_REVIEW_REQUIRED
            for item in review_items
        ),
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "live_activation_status": ACTIVATION_PROHIBITED,
        "identity_mapping_items": identity_items,
        "claim_review_items": sorted(review_items, key=lambda item: item["claim_id"]),
    }


def write_claim_review_aid(aid: dict[str, Any], output: Path) -> None:
    write_json_atomic(aid, output)