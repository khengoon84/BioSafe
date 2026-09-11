from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
INGESTION = ROOT / "controlled_sources/ingestion_v0_1"
CURATED = INGESTION / "reports/curated_candidate_kb_v0_1.json"
COMPONENTS = INGESTION / "reports/component_candidates_v0_1.json"
CROSSWALK = INGESTION / "config/document_identity_crosswalk_v0_1.json"
LIVE_KB = ROOT / "data/BioSafe_Knowledge_Base_v0.2.json"
LIVE_MANIFEST = ROOT / "data/BioSafe_Knowledge_Pack_Manifest_v0.1.json"
STATUS = "REVIEW_REQUIRED_BEFORE_CLAIM_USE"
ACTIVATION = "PROHIBITED_PENDING_PHASE_C_GATES"


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _controlled_documents(curated: dict[str, Any], components: dict[str, Any]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for chunk in components["candidate_chunks"]:
        by_id.setdefault(chunk["document_id"], chunk)
    claims = {c["controlled_document_id"]: c for c in curated["curated_claims"]}
    rows = []
    # The component artifact also contains reviewed-but-non-curated documents.
    # The benchmark corpus must be limited to the documents represented by the
    # 32 curated claims, while still retaining their exact span IDs below.
    for document_id in sorted(claims):
        chunk = by_id[document_id]
        claim = claims[document_id]
        rows.append({
            "document_id": document_id,
            "title": chunk["title"],
            "authority": "World Health Organization" if document_id.startswith("KB-WHO-") else "Official controlled source",
            "jurisdiction": claim["jurisdiction"],
            "document_type": "Controlled candidate source",
            "authority_tier": claim["authority_tier"],
            "status": "Offline curated candidate; not live activated",
            "source_url": "",
        })
    return rows


def build_artifacts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    curated, components, crosswalk = _load(CURATED), _load(COMPONENTS), _load(CROSSWALK)
    claims = []
    for source in sorted(curated["curated_claims"], key=lambda x: x["claim_id"]):
        original = source["original_claim"]
        text = " ".join([original["text"], original["section"], original["claim_type"]])
        claims.append({
            "claim_id": source["claim_id"],
            "document_id": source["controlled_document_id"],
            "text": text,
            "claim_type": original["claim_type"],
            "section": original["section"],
            "page": original["page"],
            "priority": original["priority"],
            "verification_status": original["verification_status"],
            "scope": [source["evidence_role"], original["claim_type"]],
            "support_spans": source["support_spans"],
        })
    kb = {
        "knowledge_base_id": "BioSafe_PhaseC3_Benchmark_KB_v0.1",
        "artifact_version": "BioSafe_PhaseC3_Benchmark_KB_v0.1",
        "artifact_scope": "ADDITIVE_OFFLINE_CURATED_CANDIDATE_REFERENCE_ONLY",
        "claim_use_status": STATUS,
        "live_activation_status": ACTIVATION,
        "documents": _controlled_documents(curated, components),
        "claims": claims,
        "retrieval_rules": [],
        "source_artifacts": {
            "curated_candidate_kb_sha256": hashlib.sha256(CURATED.read_bytes()).hexdigest(),
            "component_candidates_sha256": hashlib.sha256(COMPONENTS.read_bytes()).hexdigest(),
            "crosswalk_sha256": hashlib.sha256(CROSSWALK.read_bytes()).hexdigest(),
        },
    }
    manifest_records = []
    for doc in kb["documents"]:
        manifest_records.append({"record_id": doc["document_id"], "authority_tier": int(doc["authority_tier"].split()[-1]), "retrieval_priority": 90, "scope": [], "must_cite": True})
    manifest = {"version": "C3-v0.1", "artifact_version": "BioSafe_PhaseC3_Benchmark_Manifest_v0.1", "claim_use_status": STATUS, "live_activation_status": ACTIVATION, "records": manifest_records}
    cases = []
    for claim in claims:
        spans = claim["support_spans"]
        cases.append({
            "case_id": f"C3-{claim['claim_id']}", "case_type": "positive_claim_coverage",
            "query": claim["text"], "relevant_claim_ids": [claim["claim_id"]],
            "expected_source_ids": sorted({s["source_record_id"] for s in spans}),
            "expected_pages": sorted({s["pdf_page_start"] for s in spans}),
            "claim_id": claim["claim_id"], "safety_status": STATUS,
        })
    gold = {"artifact_version": "BioSafe_PhaseC3_Gold_Cases_v0.1", "case_count": len(cases), "claim_use_status": STATUS, "live_activation_status": ACTIVATION, "cases": cases}
    return kb, manifest, gold


def evaluate(kb: dict[str, Any], manifest: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from retriever_base import BioSafeCFG01
    from retriever_cfg02_base import BioSafeCFG02
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory); kb_path = base / "kb.json"; manifest_path = base / "manifest.json"
        kb_path.write_bytes(canonical_bytes(kb)); manifest_path.write_bytes(canonical_bytes(manifest))
        spans_by_claim = {claim["claim_id"]: claim.get("support_spans", []) for claim in kb["claims"]}
        results = {}
        for name, cls in (("CFG-01", BioSafeCFG01), ("CFG-02", BioSafeCFG02)):
            retriever = cls(kb_path, manifest_path)
            rows = []
            for case in gold["cases"]:
                profile, hits = retriever.retrieve(case["query"], top_k=10)
                ids = [h["claim_id"] for h in hits]
                ranks = [ids.index(i) + 1 for i in case["relevant_claim_ids"] if i in ids]
                expected = set(case["expected_source_ids"])
                # The frozen retriever deliberately returns its public record
                # fields only. Resolve exact support spans through the
                # benchmark's hash-bound claim map, not generated prose or a
                # change to the frozen retriever contract.
                retrieved_spans = {s.get("source_record_id") for hit in hits for s in spans_by_claim.get(hit["claim_id"], [])}
                cited = expected & retrieved_spans
                docs = [h["document_id"] for h in hits]
                leakage = sum(1 for h in hits if profile.jurisdiction != "System" and h["jurisdiction"] != profile.jurisdiction)
                dominant = max((docs.count(d) for d in set(docs)), default=0) / len(docs) if docs else 0.0
                rows.append({"case_id": case["case_id"], "query_profile": profile.__dict__, "ranked_claim_ids": ids, "first_relevant_rank": min(ranks) if ranks else None, "recall_at": {str(k): int(any(r <= k for r in ranks)) for k in (1, 3, 5, 10)}, "citation_completeness_at_10": len(cited) / len(expected) if expected else 0.0, "retrieved_support_span_ids_at_10": sorted(retrieved_spans), "source_diversity_at_10": len(set(docs)), "duplicate_domination_at_10": round(dominant, 6), "jurisdiction_leakage_count_at_10": leakage})
            results[name] = rows
    summary = {}
    for name, rows in results.items():
        summary[name] = {f"recall_at_{k}": sum(r["recall_at"][str(k)] for r in rows) / len(rows) for k in (1, 3, 5, 10)}
        summary[name].update({"mean_citation_completeness_at_10": sum(r["citation_completeness_at_10"] for r in rows) / len(rows), "mean_source_diversity_at_10": sum(r["source_diversity_at_10"] for r in rows) / len(rows), "max_duplicate_domination_at_10": max(r["duplicate_domination_at_10"] for r in rows), "jurisdiction_leakage_total_at_10": sum(r["jurisdiction_leakage_count_at_10"] for r in rows)})
    return {"artifact_version": "BioSafe_PhaseC3_Retrieval_Benchmark_Report_v0.1", "benchmark_mode": "DESCRIPTIVE_NO_HARD_GATE", "claim_use_status": STATUS, "live_activation_status": ACTIVATION, "case_count": len(gold["cases"]), "input_hashes": {"kb": sha256(kb), "manifest": sha256(manifest), "gold": sha256(gold)}, "summary": summary, "cases": results}