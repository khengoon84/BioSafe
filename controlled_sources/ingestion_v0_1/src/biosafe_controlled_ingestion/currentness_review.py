from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


ARTIFACT_VERSION = "BioSafe_Targeted_Currentness_Evidence_Packet_v0.1"
REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
REVIEW_COMPLETE = "HUMAN_REVIEW_COMPLETE"
OUTCOMES = {
    "CURRENTNESS_VERIFIED_FOR_EXACT_PROVISION",
    "CURRENTNESS_UNRESOLVED",
    "CONFLICTING_CURRENTNESS_EVIDENCE",
    "SUPERSEDED_OR_AMENDED_REQUIRES_TEXT_RECONCILIATION",
}
EXPECTED_HASHES = {
    "KB-MY-ACT678": "8c2badc2db503906b92a42b905736653b868ee3c7bc6fb79719e0081cf25e8cc",
    "KB-MY-REG2010": "6e8364d8e7015738863ed9194a62d16ec62f18c85f338e438a533ed98d83a756",
    "KB-MY-AMEND2019": "afcba3598e4188c6aafc452544d2dd4a4505d8f8785b4a251b6c922444d2523c",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source(register: dict[str, dict[str, str]], source_id: str) -> dict[str, str]:
    try:
        row = register[source_id]
    except KeyError as error:
        raise ValidationError(f"currentness source register record is missing: {source_id}") from error
    if row.get("sha256") != EXPECTED_HASHES[source_id]:
        raise ValidationError(f"currentness source hash mismatch: {source_id}")
    return row


def build_currentness_evidence_packet(
    source_register: list[dict[str, str]],
    source_register_bytes: bytes,
    source_policy: dict[str, Any],
    source_policy_bytes: bytes,
    amendment_artifact: dict[str, Any],
    amendment_artifact_bytes: bytes,
    exact_support_artifact: dict[str, Any],
    exact_support_artifact_bytes: bytes,
) -> dict[str, Any]:
    register = {row.get("candidate_id", ""): row for row in source_register}
    if set(EXPECTED_HASHES) - set(register):
        raise ValidationError("currentness packet requires Act, Regulations, and amendment register records")
    for source_id in EXPECTED_HASHES:
        _source(register, source_id)
    if source_policy.get("activation_default") != ACTIVATION_PROHIBITED:
        raise ValidationError("currentness source policy must prohibit activation")
    if amendment_artifact.get("amendment_document_id") != "KB-MY-AMEND2019":
        raise ValidationError("currentness packet amendment identity is invalid")
    if amendment_artifact.get("amendment_sha256") != EXPECTED_HASHES["KB-MY-AMEND2019"]:
        raise ValidationError("currentness packet amendment hash is invalid")
    if amendment_artifact.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("currentness amendment artifact must require claim review")
    if exact_support_artifact.get("claim_ids") != ["CLM-005", "CLM-007"]:
        raise ValidationError("currentness packet requires the accepted CLM-005/CLM-007 support artifact")
    provisions = [
        {
            "provision_id": "ACT678-S22-1-A-C",
            "claim_ids": ["CLM-005"],
            "instrument": "Biosafety Act 2007 [Act 678]",
            "source_id": "KB-MY-ACT678",
            "source_pages": [83, 84],
            "provision": "section 22(1)(a)–(c)",
            "evidence": [
                "Owner-designated Act 678 PDF is hash-bound and contains the section 22(1)(a)–(c) text on PDF pages 83–84.",
                "The accepted 2019 Order targets Act 678 First and Third Schedules and does not identify section 22 as an amended provision.",
            ],
            "amendment_assessment": "NO_VISIBLE_2019_ORDER_OPERATION_ON_SECTION_22",
            "currentness_outcome": "CURRENTNESS_UNRESOLVED",
            "uncertainty": "The controlled corpus does not establish a complete amendment/revocation/supersession inventory for section 22.",
        },
        {
            "provision_id": "REG2010-REG16-1-2",
            "claim_ids": ["CLM-005"],
            "instrument": "Biosafety (Approval and Notification) Regulations 2010 [P.U. (A) 367/2010]",
            "source_id": "KB-MY-REG2010",
            "source_pages": [27],
            "provision": "Regulation 16(1)–(2)",
            "evidence": [
                "The official-equivalence-verified Regulations PDF is hash-bound and contains Regulation 16(1)–(2) on PDF page 27.",
                "The accepted 2019 Order targets Act 678 schedules, not Regulation 16 or P.U. (A) 367/2010.",
            ],
            "amendment_assessment": "NO_VISIBLE_2019_ORDER_OPERATION_ON_REGULATION_16",
            "currentness_outcome": "CURRENTNESS_UNRESOLVED",
            "uncertainty": "The controlled corpus does not establish a complete amendment/revocation/supersession inventory for Regulation 16.",
        },
        {
            "provision_id": "REG2010-REG2B-FIRST-SCHEDULE",
            "claim_ids": ["CLM-007"],
            "instrument": "Biosafety (Approval and Notification) Regulations 2010 [P.U. (A) 367/2010]",
            "source_id": "KB-MY-REG2010",
            "source_pages": [21, 30, 31, 32, 33, 34],
            "provision": "Regulation 2(b) and First Schedule",
            "evidence": [
                "The official-equivalence-verified Regulations PDF is hash-bound and contains Regulation 2(b) on PDF page 21 and the reviewed First Schedule range on PDF pages 30–34.",
                "The accepted 2019 Order targets Act 678 schedules, not the First Schedule to P.U. (A) 367/2010.",
            ],
            "amendment_assessment": "NO_VISIBLE_2019_ORDER_OPERATION_ON_REGULATIONS_FIRST_SCHEDULE",
            "currentness_outcome": "CURRENTNESS_UNRESOLVED",
            "uncertainty": "The controlled corpus does not establish a complete amendment/revocation/supersession inventory for Regulation 2(b) or the First Schedule.",
        },
    ]
    return {
        "artifact_version": ARTIFACT_VERSION,
        "review_scope": "TARGETED_EXACT_PROVISION_CURRENTNESS_EVIDENCE_ONLY",
        "source_register_sha256": _sha256(source_register_bytes),
        "source_policy_sha256": _sha256(source_policy_bytes),
        "amendment_artifact_sha256": _sha256(amendment_artifact_bytes),
        "exact_support_artifact_sha256": _sha256(exact_support_artifact_bytes),
        "source_records": {
            source_id: {
                "sha256": row["sha256"],
                "title": row.get("title"),
                "identifier": row.get("identifier"),
                "status": row.get("status"),
                "currentness_status": row.get("currentness_status"),
                "supersession_status": row.get("supersession_status"),
                "official_landing_page": row.get("official_landing_page"),
                "direct_download_url": row.get("direct_download_url"),
            }
            for source_id, row in sorted(register.items())
            if source_id in EXPECTED_HASHES
        },
        "amendment_scope": {
            "target_instrument": "Biosafety Act 2007 [Act 678]",
            "non_target_instrument": "Biosafety (Approval and Notification) Regulations 2010 [P.U. (A) 367/2010]",
            "accepted_transcription": True,
            "impact_on_claims": "The accepted Order transcription does not visibly amend the provisions reviewed for CLM-005 or CLM-007.",
        },
        "provisions": provisions,
        "human_review_status": REVIEW_REQUIRED,
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "promotion_status": "NOT_PROMOTED",
        "live_activation_status": ACTIVATION_PROHIBITED,
        "required_review_actions": [
            "Verify the exact-provision amendment inventory from authoritative current legal materials.",
            "Record any later amendment, revocation, replacement, commencement, or conflict without inference.",
            "Keep currentness unresolved if the complete inventory cannot be established.",
            "Do not promote CLM-005 or CLM-007 or use this packet for a case-level authorization determination.",
        ],
    }


def write_currentness_evidence_packet(packet: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def accept_currentness_review(
    packet: dict[str, Any], *, reviewer_identity: str, reviewer_role: str, review_date: str
) -> dict[str, Any]:
    """Record review of the evidence packet without asserting current law."""
    if packet.get("human_review_status") != REVIEW_REQUIRED:
        raise ValidationError("currentness packet is not awaiting human review")
    if packet.get("promotion_status") != "NOT_PROMOTED":
        raise ValidationError("currentness review cannot accept a promoted packet")
    if packet.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("currentness packet must require claim review")
    if packet.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("currentness packet must prohibit live activation")
    if not reviewer_identity.strip() or not reviewer_role.strip():
        raise ValidationError("reviewer identity and role are required")
    provisions = packet.get("provisions")
    if not isinstance(provisions, list) or not provisions:
        raise ValidationError("currentness packet must contain provisions")
    if any(item.get("currentness_outcome") != "CURRENTNESS_UNRESOLVED" for item in provisions):
        raise ValidationError("this guarded acceptance requires every currentness outcome to remain unresolved")
    result = json.loads(json.dumps(packet))
    result["human_review_status"] = REVIEW_COMPLETE
    result["review_decision"] = {
        "decision": "ACCEPT_CURRENTNESS_REVIEW_WITH_UNRESOLVED_OUTCOMES",
        "reviewer_identity": reviewer_identity,
        "reviewer_role": reviewer_role,
        "review_date": review_date,
        "findings": [
            "The source identities, hashes, provision boundaries, and recorded evidence were reviewed.",
            "The available packet does not establish a complete authoritative amendment, commencement, revocation, replacement, or supersession history for the exact provisions.",
            "All exact-provision currentness outcomes therefore remain CURRENTNESS_UNRESOLVED.",
            "Acceptance does not establish current law, applicability, approval, notification, exemption, compliance, or permission to begin work.",
        ],
        "attestations": {
            "source_identity_and_hashes_reviewed": True,
            "exact_provision_boundaries_reviewed": True,
            "currentness_uncertainty_retained": True,
            "case_level_authorization_prohibited": True,
            "live_activation_prohibited": True,
        },
    }
    result["required_review_actions"] = [
        "Obtain authoritative evidence for the complete amendment, commencement, revocation, replacement, and supersession history of each exact provision.",
        "Keep each provision CURRENTNESS_UNRESOLVED unless exact-provision currentness is affirmatively established.",
        "Do not promote CLM-005 or CLM-007 or use this packet for a case-level authorization determination.",
    ]
    return result