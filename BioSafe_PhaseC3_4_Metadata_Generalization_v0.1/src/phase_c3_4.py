from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "BioSafe_PhaseC3_Retrieval_Benchmark_v0.1/src"))
sys.path.insert(0, str(ROOT / "BioSafe_PhaseC3_3_Retrieval_Oracle_v0.1/src"))
from retriever_base import BioSafeCFG01
from retriever_cfg02_base import BioSafeCFG02
from phase_c3_benchmark import ACTIVATION, STATUS, build_artifacts, canonical_bytes
from build_retrieval_policy import build_artifact

POLICY = ROOT / "BioSafe_PhaseC3_4_Metadata_Generalization_v0.1/data/retrieval_policy_v0_1.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _claim_rows(kb: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["claim_id"]: c for c in kb["claims"]}


def policy_valid(policy: dict[str, Any]) -> bool:
    if policy["claim_use_status"] != STATUS or policy["live_activation_status"] != ACTIVATION:
        return False
    docs = {d["controlled_document_id"]: d for d in policy["documents"]}
    # The reviewed baseline has 17 documents; onboarding tests may add a
    # metadata-only fixture without changing this minimum.
    return len(docs) >= 17 and len(docs) == len(policy["documents"]) and all(
        d["source_sha256"] for d in docs.values()
    )


class MetadataMixin:
    def __init__(self, kb_path, manifest_path, policy_path=POLICY, metadata_layer=True, **kwargs):
        self.policy = json.loads(Path(policy_path).read_text(encoding="utf-8"))
        if not policy_valid(self.policy):
            raise ValueError("invalid C3.4 retrieval policy")
        self.policy_by_doc = {d["controlled_document_id"]: d for d in self.policy["documents"]}
        self.metadata_layer = metadata_layer
        super().__init__(kb_path, manifest_path, **kwargs)

    def _eligible(self, record, profile):
        if record["record_type"] == "control_rule":
            return False
        meta = self.policy_by_doc.get(record["document_id"])
        if not meta or not meta["source_sha256"]:
            return False
        if meta["currentness_status"].startswith("OWNER_DESIGNATED"):
            return False
        return record["jurisdiction"] == profile.jurisdiction or (
            profile.jurisdiction == "Malaysia" and record["jurisdiction"] == "International")

    def _metadata_score(self, record, profile):
        if not self.metadata_layer:
            return 0.0
        meta = self.policy_by_doc[record["document_id"]]
        query_domain = str(getattr(profile, "domain", "")).lower().replace("_", " ")
        searchable = " ".join(meta["allowed_domains"] + meta["claim_types"] + meta["evidence_roles"])
        domain_hit = bool(query_domain and any(part in searchable.lower() for part in query_domain.split("-") if len(part) > 2))
        jurisdiction = 1.0 if meta["jurisdiction"] == profile.jurisdiction else 0.0
        return 0.10 * float(domain_hit) + 0.05 * jurisdiction

    def retrieve(self, query: str, top_k: int = 5):
        profile, hits = super().retrieve(query, top_k=max(top_k, 20))
        if not self.metadata_layer:
            return profile, hits[:top_k]
        for row in hits:
            row["metadata_score"] = round(self._metadata_score(row, profile), 6)
            row["final_score"] = round(float(row["final_score"]) + row["metadata_score"], 6)
        hits.sort(key=lambda x: (x["final_score"], x.get("lexical_score", 0), x.get("retrieval_priority", 0)), reverse=True)
        return profile, hits[:top_k]


class C34CFG01(MetadataMixin, BioSafeCFG01):
    pass


class C34CFG02(MetadataMixin, BioSafeCFG02):
    pass


def _heldout_queries(kb: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for c in sorted(kb["claims"], key=lambda x: x["claim_id"]):
        words = c["text"].replace("should", "is expected to").replace("guidance", "source material")
        rows.append({"case_id": "C34-H-" + c["claim_id"], "case_type": "heldout_claim",
                     "query": "Which reviewed source addresses this issue: " + words,
                     "acceptable_claim_ids": [c["claim_id"]], "expected_jurisdiction":
                     "International" if c["document_id"].startswith("KB-WHO-") else "Malaysia"})
    return rows


def _fixture(kb: dict[str, Any], policy: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    fixture_doc = "FIXTURE-AUTHORITY-001"
    fixture_claim = {"claim_id": "FIX-001", "document_id": fixture_doc,
        "text": "The synthetic fixture source describes a documented biosafety training record.",
        "claim_type": "training_record", "section": "Fixture section", "page": 1,
        "priority": "informational", "verification_status": "SYNTHETIC_FIXTURE_ONLY",
        "scope": ["training", "fixture"], "support_spans": [{
            "source_record_id": fixture_doc + ":PAGE_1", "pdf_page_start": 1, "pdf_page_end": 1,
            "quoted_support": "Synthetic fixture source: documented biosafety training record.",
            "support_type": "DIRECT", "source_kind": "SYNTHETIC_FIXTURE"}]}
    kb2 = json.loads(json.dumps(kb)); kb2["documents"].append({"document_id": fixture_doc,
        "title": "Synthetic onboarding fixture (not authoritative)", "authority": "Synthetic fixture",
        "jurisdiction": "International", "document_type": "Test fixture", "authority_tier": 3,
        "status": "Synthetic fixture; never authoritative", "source_url": ""}); kb2["claims"].append(fixture_claim)
    m2 = json.loads(json.dumps(policy)); m2["documents"].append({"controlled_document_id": fixture_doc,
        "legacy_document_ids": [fixture_doc], "title": "Synthetic onboarding fixture",
        "publisher": "BioSafe tests", "jurisdiction": "International", "authority_tier": 3,
        "document_type": "Test fixture", "publication_date": "", "currentness_status": "FIXTURE_ONLY",
        "supersession_status": "FIXTURE_ONLY", "allowed_domains": ["training"], "excluded_domains": [],
        "claim_types": ["training_record"], "evidence_roles": ["synthetic_fixture"],
        "boundary_tags": [], "source_sha256": hashlib.sha256(b"synthetic-fixture").hexdigest(),
        "curated_claim_count": 1})
    return kb2, m2, {"case_id": "C34-FIX-001", "case_type": "new_document_fixture", "query": fixture_claim["text"], "acceptable_claim_ids": ["FIX-001"], "expected_jurisdiction": "International"}


def _run(cls, kb, manifest, policy, cases, metadata_layer=True):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td); kp = p / "kb.json"; mp = p / "manifest.json"; pp = p / "policy.json"
        kp.write_bytes(canonical_bytes(kb)); mp.write_bytes(canonical_bytes(manifest)); pp.write_bytes(canonical_bytes(policy))
        r = cls(kp, mp, policy_path=pp, metadata_layer=metadata_layer); results = []
        for case in cases:
            profile, hits = r.retrieve(case["query"], top_k=10); ids = [h["claim_id"] for h in hits]
            ranks = [ids.index(x) + 1 for x in case["acceptable_claim_ids"] if x in ids]
            results.append({"case_id": case["case_id"], "case_type": case["case_type"], "ranked_claim_ids": ids,
                "query_profile": profile.__dict__, "first_acceptable_rank": min(ranks) if ranks else None,
                "recall_at_10": int(bool(ranks)), "route_ok": profile.jurisdiction == case["expected_jurisdiction"]})
        return results


def evaluate() -> dict[str, Any]:
    kb, manifest, _ = build_artifacts(); policy = build_artifact(); heldout = _heldout_queries(kb)
    fixture_kb, fixture_policy, fixture_case = _fixture(kb, policy)
    cases = heldout + [fixture_case]
    variants = {"C34_METADATA_CFG01": C34CFG01, "C34_METADATA_CFG02": C34CFG02}
    runs = {}
    for name, cls in variants.items():
        runs[name] = {"metadata_on": _run(cls, fixture_kb, manifest, fixture_policy, cases, True),
                      "metadata_off": _run(cls, fixture_kb, manifest, fixture_policy, cases, False)}
    summary = {}
    for name, modes in runs.items():
        on = modes["metadata_on"]; held = [x for x in on if x["case_type"] == "heldout_claim"]; fix = [x for x in on if x["case_type"] == "new_document_fixture"]
        summary[name] = {"heldout_recall_at_10": sum(x["recall_at_10"] for x in held) / len(held),
                         "heldout_route_accuracy": sum(x["route_ok"] for x in held) / len(held),
                         "new_document_recall_at_10": int(fix[0]["recall_at_10"]),
                         "metadata_layer_changed_rankings": on != modes["metadata_off"]}
    return {"artifact_version": "BioSafe_PhaseC3_4_Metadata_Generalization_Report_v0.1",
        "benchmark_mode": "C3_4_HELDOUT_AND_ONBOARDING_GATE_REVIEW", "gate_result": "BLOCKED_PENDING_OWNER_REVIEW",
        "claim_use_status": STATUS, "live_activation_status": ACTIVATION,
        "policy_hash": hashlib.sha256(canonical_bytes(policy)).hexdigest(), "summary": summary,
        "cases": runs, "heldout_case_count": len(heldout), "new_document_fixture": fixture_case}


def artifacts():
    kb, manifest, _ = build_artifacts(); policy = build_artifact()
    return kb, manifest, policy, {"cases": _heldout_queries(kb)}