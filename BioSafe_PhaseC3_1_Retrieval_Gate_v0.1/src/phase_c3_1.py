from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "BioSafe_PhaseC3_Retrieval_Benchmark_v0.1/src"))
sys.path.insert(0, str(ROOT / "src"))
from phase_c3_benchmark import ACTIVATION, STATUS, build_artifacts, canonical_bytes

CROSSWALK = ROOT / "controlled_sources/ingestion_v0_1/config/document_identity_crosswalk_v0_1.json"
CURATED = ROOT / "controlled_sources/ingestion_v0_1/reports/curated_candidate_kb_v0_1.json"
COMPONENTS = ROOT / "controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json"
EXPECTED_CROSSWALK_VERSION = "BioSafe_Document_Identity_Crosswalk_v0.1"
ALIASES = {
    "KB-MY-DOE2005": "KB-MY-SW2005", "KB-MY-MOH2023": "KB-MY-TRANSPORT2023",
    "KB-WHO-PPE": "KB-WHO-LBM4-PPE", "KB-WHO-RA": "KB-WHO-LBM4-RA",
}


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def crosswalk_mapping() -> dict[str, str]:
    data = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    if data.get("crosswalk_version") != EXPECTED_CROSSWALK_VERSION:
        raise ValueError("crosswalk version mismatch")
    if data.get("claim_use_status") != STATUS or data.get("live_activation_status") != ACTIVATION:
        raise ValueError("crosswalk safety status mismatch")
    mapping = {row["legacy_document_id"]: row["controlled_document_id"] for row in data["document_mappings"]}
    if any(ALIASES.get(k, k) != v for k, v in mapping.items()):
        raise ValueError("crosswalk mapping differs from reviewed identity mapping")
    components = json.loads(COMPONENTS.read_text(encoding="utf-8"))
    hashes = {}
    for chunk in components["candidate_chunks"]:
        hashes.setdefault(chunk["document_id"], set()).add(chunk["source_sha256"])
    if any(len(values) != 1 for values in hashes.values()):
        raise ValueError("curated source hashes are inconsistent")
    source_hash_by_controlled = {document_id: next(iter(values)) for document_id, values in hashes.items()}
    for row in data["document_mappings"]:
        if source_hash_by_controlled.get(row["controlled_document_id"]) != row["source_sha256"]:
            raise ValueError("crosswalk source hash is not bound to curated claims")
    return mapping


class CrosswalkAwareMixin:
    """Eligibility-only adapter; frozen ranking and returned controlled IDs remain intact."""

    def _eligible(self, record: dict[str, Any], profile: Any) -> bool:
        if record["record_type"] == "control_rule":
            return super()._eligible(record, profile)
        document_id = record["document_id"]
        domains = {
            "TRANSPORT": {"KB-MY-TRANSPORT2023"},
            "WASTE": {"KB-MY-SW2005", "KB-MY-CU", "KB-WHO-LBM4"},
            "MY-FORME": {"KB-MY-FORME", "KB-MY-GMMRA"},
            "MY-IBC": {"KB-MY-IBC", "KB-MY-REG2010"},
            "MY-INCIDENT": {"KB-MY-ACT678", "KB-MY-CU", "KB-MY-IBC"},
            "MY-RA": {"KB-MY-GMMRA", "KB-MY-ACT678"},
            "WHO-RA": {"KB-WHO-LBM4-RA", "KB-WHO-LBM4"},
            "WHO-BIOSEC": {"KB-WHO-BIOSEC"},
            "AUTHORITY": {"KB-MY-ACT678", "KB-MY-REG2010"},
            "CURRENTNESS": {"KB-MY-FORME"},
            "MY-REG": {"KB-MY-ACT678", "KB-MY-REG2010", "KB-MY-CU", "KB-MY-GMMRA", "KB-MY-IBC"},
        }
        if profile.domain in domains:
            return document_id in domains[profile.domain]
        return super()._eligible(record, profile)


def adapters():
    from retriever_base import BioSafeCFG01
    from retriever_cfg02_base import BioSafeCFG02
    return (BioSafeCFG01, BioSafeCFG02,
            type("BioSafeC31CFG01", (CrosswalkAwareMixin, BioSafeCFG01), {}),
            type("BioSafeC31CFG02", (CrosswalkAwareMixin, BioSafeCFG02), {}))


def _paraphrase(claim: dict[str, Any]) -> str:
    templates = {
        "transport": "What does the Malaysian clinical specimen transport guidance say about safe transport, classification, packaging, and marking?",
        "incident": "What reporting and emergency arrangements are described for laboratory incidents?",
        "risk_assessment": "What should a biological risk assessment consider before controls are selected?",
        "uncertainty": "How should missing information and uncertainty be handled in this risk assessment?",
        "ppe_role": "Is PPE alone enough to establish laboratory safety, or is it part of broader controls?",
        "ppe_risk_based_selection": "When should additional respiratory protection be considered?",
    }
    return templates.get(claim["claim_type"], f"What does the controlled guidance say about {claim['claim_type'].replace('_', ' ')}?")


def build_gold(kb: dict[str, Any]) -> dict[str, Any]:
    cases = []
    for claim in kb["claims"]:
        spans = claim.get("support_spans", [])
        common = {"expected_claim_ids": [claim["claim_id"]], "expected_source_ids": sorted({s["source_record_id"] for s in spans}), "expected_pages": sorted({s["pdf_page_start"] for s in spans}), "forbidden_claim_ids": [], "safety_status": STATUS}
        cases.append({"case_id": f"C31-P-{claim['claim_id']}", "case_type": "positive", "query": claim["text"], **common})
        cases.append({"case_id": f"C31-Q-{claim['claim_id']}", "case_type": "paraphrase", "query": _paraphrase(claim), **common})
    boundaries = [
        ("WHO-not-Malaysian-law", "Is WHO laboratory biosafety guidance Malaysian law?", ["KB-MY-ACT678", "KB-MY-REG2010"]),
        ("handling-not-transport", "Does laboratory handling guidance establish clinical specimen transport requirements?", ["KB-MY-TRANSPORT2023"]),
        ("transport-not-containment", "Does a clinical specimen transport guideline establish laboratory containment level?", ["KB-MY-CU"]),
        ("generic-GM-not-LMO", "Does generic genetic modification by itself establish that a project is an LMO activity?", ["KB-MY-CU"]),
        ("biological-waste-not-SW404", "Is all biological laboratory waste automatically SW 404 scheduled waste?", ["KB-MY-SW2005"]),
        ("BSC-not-level", "Does mentioning a Class II biological safety cabinet establish the biosafety level?", ["KB-MY-CU"]),
        ("Form-E-not-approval", "Does Form E itself constitute approval to begin work?", ["KB-MY-FORME"]),
    ]
    for name, query, forbidden in boundaries:
        cases.append({"case_id": f"C31-B-{name}", "case_type": "boundary_control", "query": query, "expected_claim_ids": [], "expected_source_ids": [], "expected_pages": [], "forbidden_claim_ids": forbidden, "safety_status": STATUS})
    return {"artifact_version": "BioSafe_PhaseC3_1_Gold_Cases_v0.1", "case_count": len(cases), "positive_count": 32, "paraphrase_count": 32, "boundary_count": 7, "claim_use_status": STATUS, "live_activation_status": ACTIVATION, "cases": cases}


def _run(cls: Any, kb: dict[str, Any], manifest: dict[str, Any], gold: dict[str, Any]) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory); kp = path / "kb.json"; mp = path / "manifest.json"
        kp.write_bytes(canonical_bytes(kb)); mp.write_bytes(canonical_bytes(manifest)); retriever = cls(kp, mp)
        output = []
        for case in gold["cases"]:
            profile, hits = retriever.retrieve(case["query"], top_k=10)
            ids = [hit["claim_id"] for hit in hits]
            expected = set(case["expected_claim_ids"]); forbidden = set(case["forbidden_claim_ids"])
            ranks = [ids.index(item) + 1 for item in expected if item in ids]
            top3_forbidden = sorted(forbidden & set(ids[:3]))
            output.append({"case_id": case["case_id"], "case_type": case["case_type"], "query_profile": profile.__dict__, "ranked_claim_ids": ids, "first_relevant_rank": min(ranks) if ranks else None, "forbidden_top3": top3_forbidden, "recall_at_10": int(bool(ranks)), "boundary_preserved": not top3_forbidden if case["case_type"] == "boundary_control" else True})
        return output


def evaluate() -> dict[str, Any]:
    mapping = crosswalk_mapping(); kb, manifest, _ = build_artifacts(); gold = build_gold(kb)
    frozen01, frozen02, candidate01, candidate02 = adapters()
    runs = {"FROZEN_CFG01": _run(frozen01, kb, manifest, gold), "FROZEN_CFG02": _run(frozen02, kb, manifest, gold)}
    # The additive adapter is intentionally the only candidate variant in C3.1.
    runs["C31_CROSSWALK_CFG01"] = _run(candidate01, kb, manifest, gold)
    runs["C31_CROSSWALK_CFG02"] = _run(candidate02, kb, manifest, gold)
    summary = {}
    for name, rows in runs.items():
        positives = [row for row in rows if row["case_type"] in {"positive", "paraphrase"}]
        boundaries = [row for row in rows if row["case_type"] == "boundary_control"]
        summary[name] = {"positive_or_paraphrase_recall_at_10": sum(r["recall_at_10"] for r in positives) / len(positives), "positive_no_hit_count": sum(r["first_relevant_rank"] is None for r in positives), "boundary_preservation_rate": sum(r["boundary_preserved"] for r in boundaries) / len(boundaries), "boundary_forbidden_top3_count": sum(bool(r["forbidden_top3"]) for r in boundaries)}
    hard_gates = {name: {"canonical_positive_recall_at_10": all(r["recall_at_10"] for r in rows if r["case_type"] == "positive"), "boundary_controls_preserved": all(r["boundary_preserved"] for r in rows if r["case_type"] == "boundary_control"), "activation_preserved": kb["live_activation_status"] == ACTIVATION and manifest["live_activation_status"] == ACTIVATION and gold["live_activation_status"] == ACTIVATION} for name, rows in runs.items()}
    return {"artifact_version": "BioSafe_PhaseC3_1_Retrieval_Gate_Report_v0.1", "benchmark_mode": "C3_1_GATE_REVIEW_REQUIRED", "gate_result": "BLOCKED_PENDING_OWNER_REVIEW", "claim_use_status": STATUS, "live_activation_status": ACTIVATION, "crosswalk_mapping": mapping, "input_hashes": {"curated": _digest(CURATED), "crosswalk": _digest(CROSSWALK), "kb": hashlib.sha256(canonical_bytes(kb)).hexdigest(), "gold": hashlib.sha256(canonical_bytes(gold)).hexdigest()}, "summary": summary, "hard_gates": hard_gates, "cases": runs, "gold": gold}


def artifacts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    kb, manifest, _ = build_artifacts()
    return kb, manifest, build_gold(kb)