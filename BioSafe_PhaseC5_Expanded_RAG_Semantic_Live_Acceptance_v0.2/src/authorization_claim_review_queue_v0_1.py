from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ACTIVE_KB=ROOT/"data/BioSafe_Knowledge_Base_v0.2.json"
SOURCE_REGISTER=ROOT/"controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv"
CANONICAL_REVIEW_MAP=ROOT/"controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json"
QUEUE_PATH=HERE.parent/"reports/authorization_claim_review_queue_v0_1.json"

AUTHORIZATION_SOURCE_CLAIMS={"CLM-005","CLM-007"}
NON_AUTHORIZATION_RELATED_CLAIMS={"CLM-006"}


def _sources() -> dict[str, dict[str, str]]:
    with SOURCE_REGISTER.open(encoding="utf-8",newline="") as stream:
        return {row["candidate_id"]:row for row in csv.DictReader(stream,delimiter="\t")}


def build_review_queue(kb: dict[str, Any] | None=None,
                       source_rows: dict[str, dict[str, str]] | None=None,
                       canonical_reviews: dict[str, dict[str, Any]] | None=None) -> dict[str, Any]:
    kb=kb or json.loads(ACTIVE_KB.read_text(encoding="utf-8"))
    source_rows=source_rows or _sources()
    if canonical_reviews is None:
        canonical_reviews={
            item["claim_id"]: item
            for item in json.loads(CANONICAL_REVIEW_MAP.read_text(encoding="utf-8")).get("claim_reviews", [])
            if item.get("claim_id") in AUTHORIZATION_SOURCE_CLAIMS
        }
    claims={item["claim_id"]:item for item in kb.get("claims",[])}
    entries=[]
    for claim_id in sorted(AUTHORIZATION_SOURCE_CLAIMS):
        claim=claims.get(claim_id)
        if not claim:
            continue
        source=source_rows.get(claim["document_id"],{})
        review=canonical_reviews.get(claim_id,{})
        semantic_units=review.get("semantic_units",[])
        direct_spans=review.get("support_spans",[])
        dependency_spans=review.get("dependency_support_spans",[])
        currentness=review.get("currentness_status") or "CURRENTNESS_UNRESOLVED"
        source_support=review.get("source_support_disposition")
        entries.append({
            "queue_id":f"AUTH-REVIEW-{claim_id}",
            "source_claim_id":claim_id,
            "document_id":claim["document_id"],
            "source_section":claim.get("section"),
            "source_page":claim.get("page"),
            "source_text":claim.get("text"),
            "source_sha256":source.get("sha256") or None,
            "source_currentness_status":source.get("currentness_status") or None,
            "source_supersession_status":source.get("supersession_status") or None,
            "candidate_concept":semantic_units[0].get("concept") if len(semantic_units)==1 else None,
            "candidate_polarity":semantic_units[0].get("polarity") if len(semantic_units)==1 else None,
            "candidate_normative_force":semantic_units[0].get("normative_force") if len(semantic_units)==1 else None,
            "jurisdiction":review.get("jurisdiction"),
            "material_or_technology_trigger":None,
            "specific_activity":review.get("specific_activity"),
            "authority_status":review.get("authority_status"),
            "currentness":currentness,
            "support_spans":direct_spans,
            "dependency_support_spans":dependency_spans,
            "semantic_units":semantic_units,
            "source_support_disposition":source_support,
            "human_review_status":"HUMAN_REVIEW_COMPLETE_SOURCE_SUPPORT",
            "promotion_status":review.get("promotion_status","NOT_PROMOTED"),
            "blocking_reasons":[
                "CASE_SCOPE_NOT_ESTABLISHED_BY_SOURCE_CLAIM_ALONE",
                "EXACT_PROVISION_CURRENTNESS_UNRESOLVED",
                "CASE_LEVEL_AUTHORIZATION_CONTRACT_NOT_APPROVED",
                *(["EXEMPTION_IS_NOT_A_GENERAL_NO_NOTIFICATION_DETERMINATION"] if claim_id == "CLM-007" else []),
            ],
        })
    exclusions=[]
    for claim_id in sorted(NON_AUTHORIZATION_RELATED_CLAIMS):
        claim=claims.get(claim_id)
        if claim:
            exclusions.append({
                "source_claim_id":claim_id,
                "document_id":claim["document_id"],
                "claim_type":claim.get("claim_type"),
                "reason":"Procedural/quality statement is not by itself evidence of an authorization requirement.",
                "promotion_status":"EXCLUDED_FROM_AUTHORIZATION_QUEUE",
            })
    return {
        "artifact_version":"BioSafe_C5_Authorization_Claim_Review_Queue_v0.1",
        "purpose":"Offline human-review queue only; no claim in this artifact is approved, authoritative, or connected to live retrieval.",
        "active_kb_modified":False,
        "live_retrieval_connected":False,
        "claim_use_status":"REVIEW_REQUIRED_BEFORE_CLAIM_USE",
        "live_activation_status":"PROHIBITED_PENDING_PHASE_C_GATES",
        "queue_entries":entries,
        "excluded_related_claims":exclusions,
        "source_level_follow_up":[
            {"document_id":"KB-MY-ACT678","task":"Maintain the reviewed Act 678 section 22(1)(a)–(c) scope dependency for CLM-005; exact-provision currentness remains unresolved.","status":"REVIEWED_SCOPE_DEPENDENCY_CURRENTNESS_UNRESOLVED"},
            {"document_id":"KB-MY-REG2010","task":"Maintain the reviewed Regulation 16, Regulation 2(b), and First Schedule source support; exact-provision currentness remains unresolved.","status":"SOURCE_SUPPORT_REVIEWED_CURRENTNESS_UNRESOLVED"},
        ],
    }


def write_review_queue(path: Path=QUEUE_PATH) -> dict[str, Any]:
    queue=build_review_queue()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(queue,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return queue


if __name__=="__main__":
    print(json.dumps(write_review_queue(),ensure_ascii=False,indent=2))