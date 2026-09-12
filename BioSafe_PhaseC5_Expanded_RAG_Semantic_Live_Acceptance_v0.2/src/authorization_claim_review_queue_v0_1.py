from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ACTIVE_KB=ROOT/"data/BioSafe_Knowledge_Base_v0.2.json"
SOURCE_REGISTER=ROOT/"controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv"
QUEUE_PATH=HERE.parent/"reports/authorization_claim_review_queue_v0_1.json"

AUTHORIZATION_SOURCE_CLAIMS={"CLM-005","CLM-007"}
NON_AUTHORIZATION_RELATED_CLAIMS={"CLM-006"}


def _sources() -> dict[str, dict[str, str]]:
    with SOURCE_REGISTER.open(encoding="utf-8",newline="") as stream:
        return {row["candidate_id"]:row for row in csv.DictReader(stream,delimiter="\t")}


def build_review_queue(kb: dict[str, Any] | None=None,
                       source_rows: dict[str, dict[str, str]] | None=None) -> dict[str, Any]:
    kb=kb or json.loads(ACTIVE_KB.read_text(encoding="utf-8"))
    source_rows=source_rows or _sources()
    claims={item["claim_id"]:item for item in kb.get("claims",[])}
    entries=[]
    for claim_id in sorted(AUTHORIZATION_SOURCE_CLAIMS):
        claim=claims.get(claim_id)
        if not claim:
            continue
        source=source_rows.get(claim["document_id"],{})
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
            "candidate_concept":None,
            "candidate_polarity":None,
            "candidate_normative_force":None,
            "jurisdiction":None,
            "material_or_technology_trigger":None,
            "specific_activity":None,
            "authority_status":None,
            "currentness":"UNRESOLVED",
            "support_spans":[],
            "human_review_status":"PENDING_CLAIM_LEVEL_REVIEW",
            "promotion_status":"NOT_PROMOTED",
            "blocking_reasons":[
                "CONCEPT_AND_POLARITY_REQUIRE_ATOMIC_REVIEW",
                "CASE_SCOPE_NOT_ESTABLISHED_BY_SOURCE_CLAIM_ALONE",
                "CURRENTNESS_OR_AMENDMENT_RECONCILIATION_REQUIRED",
                "REQUIRED_TYPED_EVIDENCE_METADATA_NOT_YET_APPROVED",
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
            {"document_id":"KB-MY-ACT678","task":"Extract and reconcile candidate authorization provisions from the owner-designated canonical source.","status":"NOT_STARTED"},
            {"document_id":"KB-MY-REG2010","task":"Reconcile the 2019 Schedule amendment before any notification/approval claim can be considered.","status":"BLOCKED_PENDING_AMENDMENT_RECONCILIATION"},
        ],
    }


def write_review_queue(path: Path=QUEUE_PATH) -> dict[str, Any]:
    queue=build_review_queue()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(queue,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return queue


if __name__=="__main__":
    print(json.dumps(write_review_queue(),ensure_ascii=False,indent=2))