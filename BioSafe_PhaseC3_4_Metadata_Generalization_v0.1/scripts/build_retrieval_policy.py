"""Build the versioned retrieval policy artifact from reviewed metadata contracts.

This generator is deterministic. It derives the retrieval policy from:
- source_policy_v0_1.json (allowed/excluded domains, jurisdiction, tier, currentness)
- component_map_v0_1.json (source hashes, spans)
- curated_candidate_kb_v0_1.json (claims, evidence roles, support spans, exclusions)
- document_identity_crosswalk_v0_1.json (legacy -> controlled ID mapping)

Running this script produces data/retrieval_policy_v0_1.json. The artifact is the
authoritative source for metadata-driven eligibility in C3.4.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SOURCE_POLICY = ROOT / "controlled_sources/ingestion_v0_1/config/source_policy_v0_1.json"
COMPONENT_MAP = ROOT / "controlled_sources/ingestion_v0_1/config/component_map_v0_1.json"
CURATED = ROOT / "controlled_sources/ingestion_v0_1/reports/curated_candidate_kb_v0_1.json"
CROSSWALK = ROOT / "controlled_sources/ingestion_v0_1/config/document_identity_crosswalk_v0_1.json"

STATUS = "REVIEW_REQUIRED_BEFORE_CLAIM_USE"
ACTIVATION = "PROHIBITED_PENDING_PHASE_C_GATES"


def _derive_boundary_tag(text: str) -> str:
    """Convert reviewed limitation language into stable, non-interpretive tags."""
    value = _norm(text)
    patterns = (
        ("risk group", "RISK_GROUP_NOT_CONTAINMENT_LEVEL"),
        ("containment level", "NOT_ACTIVITY_SPECIFIC_CONTAINMENT_DETERMINATION"),
        ("approval", "NOT_APPROVAL_OR_AUTHORIZATION"),
        ("compliance", "NOT_COMPLIANCE_DETERMINATION"),
        ("legal pathway", "NOT_LEGAL_PATHWAY_DETERMINATION"),
        ("project specific", "NO_PROJECT_SPECIFIC_FACT_INFERENCE"),
        ("malaysian law", "WHO_GUIDANCE_NOT_MALAYSIAN_LAW"),
        ("transport", "TRANSPORT_SCOPE_LIMITATION"),
    )
    for phrase, tag in patterns:
        if phrase in value:
            return tag
    return ""

def build_policy() -> dict:
    source_policy = json.loads(SOURCE_POLICY.read_text(encoding="utf-8"))
    component_map = json.loads(COMPONENT_MAP.read_text(encoding="utf-8"))
    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    crosswalk = json.loads(CROSSWALK.read_text(encoding="utf-8"))

    # Build legacy -> controlled mapping from crosswalk
    controlled_to_legacy: dict[str, list[str]] = {}
    for row in crosswalk["document_mappings"]:
        controlled_to_legacy.setdefault(row["controlled_document_id"], []).append(row["legacy_document_id"])

    # Build component hash lookup
    component_hashes = {}
    for doc_id, doc_meta in component_map["documents"].items():
        component_hashes[doc_id] = doc_meta["source_sha256"]

    # Build document-level policy from curated claims
    documents = {}
    claim_types_by_doc: dict[str, set[str]] = {}
    evidence_roles_by_doc: dict[str, set[str]] = {}
    boundary_tags_by_doc: dict[str, set[str]] = {}

    for claim in curated["curated_claims"]:
        doc_id = claim["controlled_document_id"]
        claim_types_by_doc.setdefault(doc_id, set()).add(claim["original_claim"]["claim_type"])
        evidence_roles_by_doc.setdefault(doc_id, set()).add(claim["evidence_role"])
        for exc in claim.get("exclusions", []):
            tag = _derive_boundary_tag(exc)
            if tag:
                boundary_tags_by_doc.setdefault(doc_id, set()).add(tag)
        for lim in claim.get("limitations", []):
            tag = _derive_boundary_tag(lim)
            if tag:
                boundary_tags_by_doc.setdefault(doc_id, set()).add(tag)

    for claim in curated["curated_claims"]:
        doc_id = claim["controlled_document_id"]
        if doc_id in documents:
            continue
        source_info = source_policy["sources"].get(doc_id, {})
        legacy_ids = controlled_to_legacy.get(doc_id, [doc_id])
        documents[doc_id] = {
            "controlled_document_id": doc_id,
            "legacy_document_ids": sorted(legacy_ids),
            "title": source_info.get("title", ""),
            "publisher": source_info.get("publisher", ""),
            "jurisdiction": claim["jurisdiction"],
            "authority_tier": claim["authority_tier"],
            "document_type": source_info.get("document_type", ""),
            "publication_date": source_info.get("publication_date", ""),
            "currentness_status": claim["currentness_status"],
            "supersession_status": claim["supersession_status"],
            "allowed_domains": sorted(source_info.get("allowed_domains", [])),
            "excluded_domains": sorted(source_info.get("excluded_domains", [])),
            "claim_types": sorted(claim_types_by_doc.get(doc_id, set())),
            "evidence_roles": sorted(evidence_roles_by_doc.get(doc_id, set())),
            "source_sha256": component_hashes.get(doc_id, claim["controlled_source_sha256"]),
            "boundary_tags": sorted(boundary_tags_by_doc.get(doc_id, set())),
        }
    return documents, claim_types_by_doc, evidence_roles_by_doc, boundary_tags_by_doc, source_policy, component_map, curated, crosswalk, controlled_to_legacy, component_hashes



def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def build_artifact() -> dict:
    (documents, claim_types, evidence_roles, boundary_tags, source_policy,
     component_map, curated, crosswalk, controlled_to_legacy, component_hashes) = build_policy()
    # Include every reviewed source in the policy, even where no claim is currently
    # curated. This is the contract that permits metadata-only onboarding later.
    for doc_id in sorted(source_policy["sources"]):
        if doc_id in documents:
            continue
        meta = source_policy["sources"][doc_id]
        documents[doc_id] = {
            "controlled_document_id": doc_id,
            "legacy_document_ids": sorted(controlled_to_legacy.get(doc_id, [doc_id])),
            "title": meta.get("title", ""), "publisher": meta.get("publisher", ""),
            "jurisdiction": meta.get("jurisdiction", ""),
            "authority_tier": meta.get("authority_tier", 3),
            "document_type": meta.get("document_type", ""),
            "publication_date": meta.get("publication_date", ""),
            "currentness_status": meta.get("currentness_status", ""),
            "supersession_status": meta.get("supersession_status", ""),
            "allowed_domains": sorted(meta.get("allowed_domains", [])),
            "excluded_domains": sorted(meta.get("excluded_domains", [])),
            "claim_types": [], "evidence_roles": [], "boundary_tags": [],
            "source_sha256": component_hashes.get(doc_id, ""),
            "curated_claim_count": 0,
        }
    for doc in documents.values():
        doc["curated_claim_count"] = len(claim_types.get(doc["controlled_document_id"], set()))
    return {
        "artifact_version": "BioSafe_PhaseC3_4_Retrieval_Policy_v0.1",
        "policy_scope": "ADDITIVE_OFFLINE_METADATA_POLICY_REFERENCE_ONLY",
        "claim_use_status": STATUS, "live_activation_status": ACTIVATION,
        "source_policy_version": source_policy.get("policy_version"),
        "component_map_version": component_map.get("component_map_version"),
        "crosswalk_version": crosswalk.get("crosswalk_version"),
        "documents": [documents[k] for k in sorted(documents)],
        "source_hashes": {
            "source_policy": _hash(SOURCE_POLICY), "component_map": _hash(COMPONENT_MAP),
            "curated": _hash(CURATED), "crosswalk": _hash(CROSSWALK),
        },
    }


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data"
    out.mkdir(parents=True, exist_ok=True)
    (out / "retrieval_policy_v0_1.json").write_bytes(canonical_bytes(build_artifact()))
