from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .components import ACTIVATION_PROHIBITED, CLAIM_REVIEW_REQUIRED
from .contracts import ValidationError


ARTIFACT_VERSION = "BioSafe_Exact_Support_Review_Packet_v0.1"
REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
REVIEW_COMPLETE = "HUMAN_REVIEW_COMPLETE"
TARGET_CLAIMS = ("CLM-005", "CLM-007")
EXPECTED = {
    "CLM-005": {
        "documents": {"KB-MY-ACT678", "KB-MY-REG2010"},
        "pages": {83, 84, 27},
    },
    "CLM-007": {
        "documents": {"KB-MY-REG2010"},
        "pages": {21, 30, 31, 32, 33, 34},
    },
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _candidate(index: dict[str, dict[str, Any]], chunk_id: str) -> dict[str, Any]:
    try:
        return index[chunk_id]
    except KeyError as error:
        raise ValidationError(f"required candidate is missing: {chunk_id}") from error


def _support(candidate: dict[str, Any], proposition: int, quote: str) -> dict[str, Any]:
    if quote not in candidate["text"]:
        raise ValidationError(f"support quote is not an exact substring: {candidate['candidate_chunk_id']}")
    return {
        "source_kind": "NATIVE_CANDIDATE",
        "source_record_id": candidate["candidate_chunk_id"],
        "support_type": "DIRECT",
        "atomic_proposition_indexes": [proposition],
        "pdf_page_start": candidate["pdf_page_start"],
        "pdf_page_end": candidate["pdf_page_end"],
        "quoted_support": quote,
    }


def build_exact_support_review_packet(
    component_artifact: dict[str, Any],
    component_artifact_bytes: bytes,
    *,
    amendment_artifact: dict[str, Any],
    amendment_artifact_bytes: bytes,
) -> dict[str, Any]:
    if component_artifact.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("component artifact must require claim review")
    if component_artifact.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("component artifact must prohibit live activation")
    if amendment_artifact.get("claim_use_status") != CLAIM_REVIEW_REQUIRED:
        raise ValidationError("amendment artifact must require claim review")
    if amendment_artifact.get("live_activation_status") != ACTIVATION_PROHIBITED:
        raise ValidationError("amendment artifact must prohibit live activation")
    candidates = {item["candidate_chunk_id"]: item for item in component_artifact.get("candidate_chunks", [])}
    selected_ids = {
        "CLM-005": [
            "KB-MY-ACT678:SELECTED_LOCAL_ACT_TEXT:PDF_PAGE_83",
            "KB-MY-ACT678:SELECTED_LOCAL_ACT_TEXT:PDF_PAGE_84",
            "KB-MY-REG2010:PUA367:PDF_PAGE_27",
        ],
        "CLM-007": [
            f"KB-MY-REG2010:PUA367:PDF_PAGE_{page}" for page in (21, 30, 31, 32, 33, 34)
        ],
    }
    claims = {
        "CLM-005": {
            "controlled_document_ids": ["KB-MY-ACT678", "KB-MY-REG2010"],
            "atomic_propositions": [
                "Act 678 section 22(1) lists activities that may not be undertaken without prior notification to the Board.",
                "Section 22(1)(a) concerns exportation of living modified organisms.",
                "Section 22(1)(b) concerns contained use involving living modified organisms.",
                "Section 22(1)(c) concerns importation of living modified organisms for a contained-use activity.",
                "Regulation 16(1) links prior notification to the activities specified in section 22(1)(a) to (c) of the Act.",
                "Regulation 16(2) states that notifications required under section 22(1)(b) and (c) are submitted through the routes stated in that provision.",
                "Regulation 16(2)(a) states a submission route to the Director General.",
                "Regulation 16(2)(b) states a route through an institutional biosafety committee in the circumstances stated in the provision.",
                "Regulation 16 requires the notification to be accompanied by a prescribed fee.",
            ],
            "support_specs": [
                (0, selected_ids["CLM-005"][0], "22.                   (1)                           No   person  shall undertake any   of         the following activities\nwithout         giving       prior        notification          to        the       Board:"),
                (1, selected_ids["CLM-005"][0], "           (a) exportation           of         living        modified        organisms;"),
                (2, selected_ids["CLM-005"][1], "          (b)         contained         use        involving       living       modified         organisms;"),
                (3, selected_ids["CLM-005"][1], "          (c) importation of  living  modified  organisms for purposes of\n                  undertaking      a      contained          use        activity."),
                (4, selected_ids["CLM-005"][2], "16.                                  (1)   A person undertaking any activity as specified in paragraphs 22(1)\n(a)      to      (c) of the Act shall give prior notification to the Board."),
                (5, selected_ids["CLM-005"][2], "                         (2)       The notification required under paragraphs 22(1)(b)    and    (c) of the Act\nshall be submitted—"),
                (6, selected_ids["CLM-005"][2], "                                                                              (a)      to the Director General; or"),
                (7, selected_ids["CLM-005"][2], " (b) for the purpose in accordance with the establishment of an institutional\n               biosafety committee under subregulation 5(1), to the Director General\n               through an institutional biosafety committee,"),
                (8, selected_ids["CLM-005"][2], "and shall be accompanied by a prescribed fee."),
            ],
            "limitations": [
                "Section 22 activity scope must be reviewed with the complete Act text and does not establish that a user-provided material is an LMO.",
                "The packet does not determine whether a particular activity falls within section 22 or whether another legal pathway applies.",
            ],
        },
        "CLM-007": {
            "controlled_document_ids": ["KB-MY-REG2010"],
            "atomic_propositions": [
                "Regulation 2(b) states that the Regulations do not apply to techniques and contained-use activities in relation to LMOs specified in the First Schedule.",
                "The First Schedule contains a distinct heading for contained-use activities exempted from notification.",
                "First Schedule item 1 contains conditions and exceptions for an activity with genetically modified Caenorhabditis elegans and Arabidopsis.",
                "First Schedule item 2 contains conditions for an activity involving an organism into which genetically modified somatic cells have been introduced.",
                "First Schedule item 3 concerns a host/vector system listed in the host/vector schedule and imposes donor-nucleic-acid conditions.",
                "The host/vector schedule is source material that must be retained when reviewing the host/vector criteria.",
                "The First Schedule’s later text states that a commercially available Host-Vector System is included only when fulfilling the criteria specified under item 1.",
            ],
            "support_specs": [
                (0, selected_ids["CLM-007"][0], " (b) techniques and contained use activities in relation to living modified\n              organisms as specified in the First Schedule."),
                (1, selected_ids["CLM-007"][1], "               CONTAINED USE ACTIVITIES WHICH ARE EXEMPTED FROM NOTIFICATION"),
                (2, selected_ids["CLM-007"][1], "                     1.                                                                                                                                                    An activity with genetically modified Caenorhabditis elegans and Arabidopsis,"),
                (3, selected_ids["CLM-007"][2], "             2.                                                                                     An activity with an organism into which genetically modified somatic cells"),
                (4, selected_ids["CLM-007"][2], "             3.                                                              An activity involving a host/vector system mentioned in the Host/Vector"),
                (5, selected_ids["CLM-007"][3], "Item                                                                                           Class                                                                                                                                                                                                                                                                                              Host                                                                                                                                                                                                                                                                                                                                                                                                      Vector"),
                (6, selected_ids["CLM-007"][5], "       2.                                The exemption list for Notification includes any commercially available Host-Vector System"),
            ],
            "required_pages": [21, 30, 31, 32, 33, 34],
            "limitations": [
                "Non-application under Regulation 2(b) is distinct from exemption from notification and must not be merged.",
                "A host/vector name, generic low-risk description, or contained-use label does not establish that all schedule criteria are met.",
                "The packet does not support a general no-notification conclusion or a case-level exemption determination.",
            ],
        },
    }
    entries = []
    for claim_id in TARGET_CLAIMS:
        claim = claims[claim_id]
        candidates_for_claim = [_candidate(candidates, cid) for cid in selected_ids[claim_id]]
        documents = {item["document_id"] for item in candidates_for_claim}
        pages = {item["pdf_page_start"] for item in candidates_for_claim}
        if documents != EXPECTED[claim_id]["documents"] or not EXPECTED[claim_id]["pages"].issubset(pages):
            raise ValidationError(f"required source coverage is incomplete for {claim_id}")
        supports = [
            _support(_candidate(candidates, selected_id), proposition + 1, quote)
            for proposition, selected_id, quote in claim["support_specs"]
        ]
        supported_indexes = {index for support in supports for index in support["atomic_proposition_indexes"]}
        expected_indexes = set(range(1, len(claim["atomic_propositions"]) + 1))
        if supported_indexes != expected_indexes:
            raise ValidationError(f"exact support must cover every proposition for {claim_id}")
        entries.append({
            "claim_id": claim_id,
            "controlled_document_ids": claim["controlled_document_ids"],
            "candidate_chunk_ids": selected_ids[claim_id],
            "required_pdf_pages": sorted(EXPECTED[claim_id]["pages"]),
            "semantic_units": (
                [
                    {
                        "semantic_unit_id": "CLM-005-REGULATION-16",
                        "concept": "NOTIFICATION",
                        "polarity": "REQUIRED",
                        "normative_force": "MANDATORY",
                        "evidence_role": "DIRECT_REGULATION_16_SUPPORT",
                        "source_activity_scope": [
                            "exportation of living modified organisms",
                            "contained use involving living modified organisms",
                            "importation of living modified organisms for purposes of undertaking a contained-use activity",
                        ],
                    },
                    {
                        "semantic_unit_id": "CLM-005-ACT-678-CONTEXT",
                        "concept": "REFERENCED_ACTIVITY_SCOPE",
                        "polarity": "CONTEXT_ONLY",
                        "normative_force": "CONTEXT_ONLY",
                        "evidence_role": "SECTION_22_REFERENCED_ACTIVITY_SCOPE",
                        "source_activity_scope": "Act 678 section 22(1)(a)–(c); not direct canonical support for the Regulations claim record.",
                    },
                ]
                if claim_id == "CLM-005" else [
                    {
                        "semantic_unit_id": "CLM-007-REGULATION-2B",
                        "concept": "REGULATORY_APPLICABILITY",
                        "polarity": "CONDITIONAL_NON_APPLICATION",
                        "normative_force": "CONDITIONAL",
                        "evidence_role": "DIRECT_REGULATION_2B_SUPPORT",
                        "source_activity_scope": "Techniques and contained-use activities in relation to LMOs specified in the First Schedule.",
                    },
                    {
                        "semantic_unit_id": "CLM-007-FIRST-SCHEDULE-EXEMPTION",
                        "concept": "NOTIFICATION",
                        "polarity": "CONDITIONAL_EXEMPTION",
                        "normative_force": "CONDITIONAL",
                        "evidence_role": "DIRECT_FIRST_SCHEDULE_SUPPORT",
                        "source_activity_scope": "First Schedule contained-use activity criteria, including item-specific conditions and host/vector/donor-nucleic-acid conditions.",
                    },
                ]
            ),
            "atomic_propositions": claim["atomic_propositions"],
            "support_spans": supports,
            "limitations": claim["limitations"],
            "authority_status": None,
            "currentness": "UNRESOLVED",
            "candidate_concept": None,
            "candidate_polarity": None,
            "candidate_normative_force": None,
            "jurisdiction": None,
            "specific_activity": None,
            "review_status": REVIEW_REQUIRED,
            "promotion_status": "NOT_PROMOTED",
            "allowed_decision_types": [],
            "allowed_actions": [],
            "reviewer_identity": None,
            "reviewer_role": None,
            "review_date": None,
            "findings": [],
            "check_results": {key: None for key in (
                "source_pages_compared", "source_quotes_compared", "atomic_proposition_wording_reviewed",
                "authority_and_jurisdiction_reviewed", "limitations_and_exclusions_reviewed",
                "case_level_use_prohibited", "live_activation_prohibited",
            )},
            "attestations": {
                "controlled_source_compared": False,
                "historical_verification_not_relied_on": False,
                "not_live_activation_acknowledged": False,
            },
        })
    return {
        "artifact_version": ARTIFACT_VERSION,
        "source_component_artifact_sha256": _sha256(component_artifact_bytes),
        "source_amendment_artifact_sha256": _sha256(amendment_artifact_bytes),
        "review_scope": "EXACT_SOURCE_SUPPORT_PREPARATION_ONLY",
        "claim_ids": list(TARGET_CLAIMS),
        "entries": entries,
        "claim_use_status": CLAIM_REVIEW_REQUIRED,
        "live_activation_status": ACTIVATION_PROHIBITED,
        "promotion_status": "NOT_PROMOTED",
        "human_review_status": REVIEW_REQUIRED,
        "review_decision": None,
        "required_human_review_actions": [
            "Compare every quoted support span with the immutable staged source PDF.",
            "Confirm atomic proposition wording, normative force, authority, jurisdiction, currentness, and limitations.",
            "Complete amendment/currentness review for the cited Act and Regulations provisions.",
            "Do not promote either claim or use this packet for a case-level authorization determination.",
        ],
    }


def write_exact_support_review_packet(packet: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def accept_source_support_review(
    packet: dict[str, Any], *, reviewer_identity: str, reviewer_role: str, review_date: str
) -> dict[str, Any]:
    """Record human acceptance of source support without resolving law or applicability."""
    if packet.get("human_review_status") != REVIEW_REQUIRED:
        raise ValidationError("exact-support packet is not awaiting human review")
    if packet.get("promotion_status") != "NOT_PROMOTED":
        raise ValidationError("source-support acceptance cannot accept a promoted packet")
    if not reviewer_identity.strip() or not reviewer_role.strip():
        raise ValidationError("reviewer identity and role are required")
    result = json.loads(json.dumps(packet))
    result["human_review_status"] = REVIEW_COMPLETE
    result["review_decision"] = {
        "decision": "ACCEPT_EXACT_SUPPORT_PACKET_AS_REVIEWED",
        "reviewer_identity": reviewer_identity,
        "reviewer_role": reviewer_role,
        "review_date": review_date,
        "findings": [
            "The proposed source excerpts were reviewed against the identified controlled source pages.",
            "The source-level propositions are accepted subject to the recorded limitations.",
            "Acceptance does not establish complete currentness, case-specific applicability, approval, compliance, exemption, or permission to begin work.",
            "CLM-005 and CLM-007 remain unavailable for case-level authorization determinations.",
        ],
        "attestations": {
            "controlled_source_compared": True,
            "historical_verification_not_relied_on": True,
            "not_live_activation_acknowledged": True,
        },
    }
    for entry in result["entries"]:
        entry["review_status"] = REVIEW_COMPLETE
        entry["support_review_status"] = "ACCEPTED_AS_SOURCE_SUPPORT"
        entry["authority_status"] = "AUTHORITATIVE_SOURCE_IDENTITY_VERIFIED_CURRENTNESS_UNRESOLVED"
        entry["jurisdiction"] = "Malaysia"
        entry["reviewer_identity"] = reviewer_identity
        entry["reviewer_role"] = reviewer_role
        entry["review_date"] = review_date
        entry["check_results"] = {key: "PASS" for key in entry["check_results"]}
        entry["attestations"] = {
            "controlled_source_compared": True,
            "historical_verification_not_relied_on": True,
            "not_live_activation_acknowledged": True,
        }
        entry["findings"] = [
            "Exact source support was accepted as transcribed for source-level review.",
            "Currentness and case-specific applicability remain unresolved.",
        ]
    result["required_human_review_actions"] = [
        "Complete amendment/currentness review for the cited Act and Regulations provisions.",
        "Resolve the cross-document dependency structure for CLM-005 before canonical claim curation.",
        "Resolve the atomic semantic split for CLM-007 before canonical claim curation.",
        "Do not promote either claim or use this packet for a case-level authorization determination.",
    ]
    return result