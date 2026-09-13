#!/usr/bin/env python3
"""Refresh additive C5 authorization artifacts from controlled review records."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
MAP = ROOT / "controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json"
QUEUE = HERE / "reports/authorization_claim_review_queue_v0_1.json"
EXTRACTION = HERE / "reports/authorization_claim_source_extraction_packet_v0_1.json"
HASHES = HERE / "reports/c5_typed_authorization_architecture_hashes_v0_1.json"
TARGETS = {"CLM-005", "CLM-007"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh() -> None:
    review_map = json.loads(MAP.read_text(encoding="utf-8"))
    reviews = {
        item["claim_id"]: item
        for item in review_map["claim_reviews"]
        if item.get("claim_id") in TARGETS
    }

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    for entry in queue["queue_entries"]:
        review = reviews[entry["source_claim_id"]]
        entry["support_spans"] = review["support_spans"]
        entry["dependency_support_spans"] = review.get("dependency_support_spans", [])
        entry["semantic_units"] = review["semantic_units"]
        entry["source_support_disposition"] = review["source_support_disposition"]
        entry["human_review_status"] = "HUMAN_REVIEW_COMPLETE_SOURCE_SUPPORT"
        entry["currentness"] = review["currentness_status"]
        entry["authority_status"] = review.get("authority_status")
        entry["jurisdiction"] = review.get("jurisdiction")
        entry["blocking_reasons"] = [
            "CASE_SCOPE_NOT_ESTABLISHED_BY_SOURCE_CLAIM_ALONE",
            "EXACT_PROVISION_CURRENTNESS_UNRESOLVED",
            "CASE_LEVEL_AUTHORIZATION_CONTRACT_NOT_APPROVED",
        ]
    queue["review_status"] = "HUMAN_REVIEW_COMPLETE_SOURCE_SUPPORT_CURRENTNESS_UNRESOLVED"
    queue["review_decision_record"]["remaining_blockers"] = [
        "COMPLETE_AMENDMENT_AND_CLAIM_CURRENTNESS_REVIEW_REQUIRED",
        "CASE_SPECIFIC_APPLICABILITY_REQUIRES_STRUCTURED_FACTS",
        "CASE_LEVEL_AUTHORIZATION_CONTRACT_NOT_APPROVED",
    ]
    queue["source_level_follow_up"] = [
        {"document_id": "KB-MY-ACT678", "task": "Maintain the reviewed Act 678 section 22(1)(a)–(c) scope dependency for CLM-005; exact-provision currentness remains unresolved.", "status": "REVIEWED_SCOPE_DEPENDENCY_CURRENTNESS_UNRESOLVED"},
        {"document_id": "KB-MY-REG2010", "task": "Maintain the reviewed Regulation 16, Regulation 2(b), and First Schedule source support; exact-provision currentness remains unresolved.", "status": "SOURCE_SUPPORT_REVIEWED_CURRENTNESS_UNRESOLVED"},
    ]
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    extraction = json.loads(EXTRACTION.read_text(encoding="utf-8"))
    for entry in extraction["entries"]:
        review = reviews[entry["source_claim_id"]]
        entry["support_spans"] = review["support_spans"]
        entry["dependency_support_spans"] = review.get("dependency_support_spans", [])
        entry["semantic_units"] = review["semantic_units"]
        entry["source_support_disposition"] = review["source_support_disposition"]
        entry["human_review_status"] = "HUMAN_REVIEW_COMPLETE_SOURCE_SUPPORT"
        entry["authority_status"] = review.get("authority_status")
        entry["jurisdiction"] = review.get("jurisdiction")
        entry["currentness"] = review["currentness_status"]
        entry["blocking_reasons"] = [
            "COMPLETE_AMENDMENT_AND_CLAIM_CURRENTNESS_REVIEW_REQUIRED",
            "CASE_SPECIFIC_APPLICABILITY_REQUIRES_STRUCTURED_FACTS",
            "CASE_LEVEL_AUTHORIZATION_CONTRACT_NOT_APPROVED",
            *(["EXEMPTION_IS_NOT_A_GENERAL_NO_NOTIFICATION_DETERMINATION"] if entry["source_claim_id"] == "CLM-007" else []),
        ]
    extraction["review_status"] = "HUMAN_REVIEW_COMPLETE_SOURCE_SUPPORT_CURRENTNESS_UNRESOLVED"
    extraction["review_decision_record"]["remaining_blockers"] = [
        "COMPLETE_AMENDMENT_AND_CLAIM_CURRENTNESS_REVIEW_REQUIRED",
        "CASE_SPECIFIC_APPLICABILITY_REQUIRES_STRUCTURED_FACTS",
        "CASE_LEVEL_AUTHORIZATION_CONTRACT_NOT_APPROVED",
    ]
    extraction["required_next_review_actions"] = [
        "Obtain authoritative exact-provision currentness evidence.",
        "Keep currentness unresolved unless exact-provision currentness is affirmatively established.",
        "Do not add entries to the active KB or use them for case-level authorization.",
    ]
    EXTRACTION.write_text(json.dumps(extraction, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    manifest = json.loads(HASHES.read_text(encoding="utf-8"))
    for relative in list(manifest.get("files", {})):
        path = ROOT / relative
        if path.exists():
            manifest["files"][relative] = sha(path)
    manifest["human_review_update"] = {
        "active_kb_modified": False,
        "entries": ["CLM-005", "CLM-007"],
        "promotion_status": "NOT_PROMOTED",
        "reviewer_action": "APPROVED_GUARDED_SOURCE_SUPPORT_WITH_CURRENTNESS_UNRESOLVED",
        "status": "HUMAN_REVIEW_COMPLETE_SOURCE_SUPPORT_CURRENTNESS_UNRESOLVED",
    }
    manifest["offline_claim_review_queue"]["result"] = "SOURCE_SUPPORT_REVIEWED_CURRENTNESS_UNRESOLVED"
    manifest["offline_source_extraction"]["status"] = "SOURCE_SUPPORT_REVIEWED_CURRENTNESS_UNRESOLVED"
    manifest["integrity_check"] = {
        "hashes_recomputed_from_current_files": True,
        "active_kb_modified": False,
        "claim_support_and_currentness_gates_preserved": True,
    }
    HASHES.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    refresh()
    print("refreshed C5 authorization queue, extraction packet, and architecture hashes")