from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "BioSafe_PhaseC3_Retrieval_Benchmark_v0.1/src"))
from phase_c3_benchmark import ACTIVATION, STATUS, build_artifacts, canonical_bytes

CROSSWALK = ROOT / "controlled_sources/ingestion_v0_1/config/document_identity_crosswalk_v0_1.json"
COMPONENTS = ROOT / "controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json"
CURATED = ROOT / "controlled_sources/ingestion_v0_1/reports/curated_candidate_kb_v0_1.json"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reviewed_crosswalk() -> dict[str, str]:
    data = json.loads(CROSSWALK.read_text(encoding="utf-8"))
    if data.get("crosswalk_version") != "BioSafe_Document_Identity_Crosswalk_v0.1":
        raise ValueError("unexpected crosswalk version")
    if data.get("claim_use_status") != STATUS or data.get("live_activation_status") != ACTIVATION:
        raise ValueError("crosswalk safety status is not preserved")
    mapping = {row["legacy_document_id"]: row["controlled_document_id"] for row in data["document_mappings"]}
    components = json.loads(COMPONENTS.read_text(encoding="utf-8"))
    hashes: dict[str, set[str]] = {}
    for chunk in components["candidate_chunks"]:
        hashes.setdefault(chunk["document_id"], set()).add(chunk["source_sha256"])
    if any(len(values) != 1 for values in hashes.values()):
        raise ValueError("component source hash is inconsistent")
    for row in data["document_mappings"]:
        if hashes.get(row["controlled_document_id"], set()) != {row["source_sha256"]}:
            raise ValueError("crosswalk source hash does not match component artifact")
    return mapping


class CrosswalkEligibilityMixin:
    def __init__(self, kb_path, manifest_path, *args, **kwargs):
        self.identity_crosswalk = reviewed_crosswalk()
        super().__init__(kb_path, manifest_path, *args, **kwargs)

    def _eligible(self, record, profile):
        if record["record_type"] == "control_rule":
            return super()._eligible(record, profile)
        allowed_legacy = {
            "TRANSPORT": {"KB-MY-MOH2023"},
            "WASTE": {"KB-MY-DOE2005", "KB-MY-CU", "KB-WHO-LBM4"},
            "MY-FORME": {"KB-MY-FORME", "KB-MY-GMMRA"},
            "MY-IBC": {"KB-MY-IBC", "KB-MY-REG2010"},
            "MY-INCIDENT": {"KB-MY-ACT678", "KB-MY-CU", "KB-MY-IBC"},
            "MY-RA": {"KB-MY-GMMRA", "KB-MY-ACT678"},
            "WHO-RA": {"KB-WHO-RA", "KB-WHO-LBM4"},
            "WHO-BIOSEC": {"KB-WHO-BIOSEC"},
            "AUTHORITY": {"KB-MY-ACT678", "KB-MY-REG2010"},
            "CURRENTNESS": {"KB-MY-FORME"},
            "MY-REG": {"KB-MY-ACT678", "KB-MY-REG2010", "KB-MY-CU", "KB-MY-GMMRA", "KB-MY-IBC"},
        }
        if profile.domain in allowed_legacy:
            return record["document_id"] in {self.identity_crosswalk.get(x, x) for x in allowed_legacy[profile.domain]}
        return super()._eligible(record, profile)


def classes():
    from retriever_base import BioSafeCFG01
    from retriever_cfg02_base import BioSafeCFG02
    from integration_authority_router_v0_1 import BioSafeIntegrationAuthorityRouterV01
    return (
        BioSafeCFG01, BioSafeCFG02,
        BioSafeIntegrationAuthorityRouterV01,
        type("C32CFG01", (CrosswalkEligibilityMixin, BioSafeCFG01), {}),
        type("C32CFG02", (CrosswalkEligibilityMixin, BioSafeCFG02), {}),
        type("C32Integration", (CrosswalkEligibilityMixin, BioSafeIntegrationAuthorityRouterV01), {}),
    )


PARAPHRASES = {
    "CLM-008": "Within Malaysian LMO contained-use guidance, what GM-BSL2 work-practice examples address access, training, waste, and incidents?",
    "CLM-009": "For a GM-BSL2 spill that may expose people to LMO material, who must be notified and what emergency process applies?",
    "CLM-010": "When contained-use work presents an aerosol or respiratory risk, what equipment does the Malaysian guidance identify?",
    "CLM-011": "What does the Malaysian contained-use guidance cover for biological waste handling, disposal, transfer, storage, and facility needs?",
    "CLM-012": "For a Malaysian GMM, which hazards, exposure or release routes, controls, and BSL considerations belong in risk assessment?",
    "CLM-013": "What background detail and treatment of uncertainty should reviewers see in a defensible Malaysian GMM assessment?",
    "CLM-014": "Should a Malaysian GMM risk assessment be revisited over time rather than treated as final?",
    "CLM-015": "What facilities, procedures, training, containment, forms, incidents, and emergency matters fall within Malaysian IBC functions?",
    "CLM-016": "What is the principal investigator's accountability relationship to the Malaysian IBC and biosafety rules?",
    "CLM-017": "Where should a relevant incident or occupational exposure be reported under the Malaysian IBC guidance?",
    "CLM-021": "Which human-health and unintentional-release risks does the Form E risk section ask applicants to describe?",
    "CLM-022": "In Form E, what precautions concern off-site transport, decontamination, disposal, isolation, and contingencies?",
    "CLM-023": "What premises and facility identification, BSL, inspection, certification, and BSO details does Form E request?",
    "CLM-024": "How does Form E address confidential business information and the justification for keeping it confidential?",
    "CLM-025": "Who completes the IBC Assessment Report in the Form E process, and is it a researcher field?",
    "CLM-026": "According to Malaysia's 2023 MOH document, how are clinical specimens and infectious substances classified and packaged for transport?",
    "CLM-027": "What triple-packaging practice does the 2023 Malaysian clinical-specimen transport guideline describe?",
    "CLM-028": "What is the scope boundary between the Malaysian clinical-specimen transport guidance and waste disposal rules?",
    "CLM-031": "How does WHO LBM4 balance biosafety measures against the actual activity risk on a case-by-case basis?",
    "CLM-032": "In WHO LBM4 risk assessment, how do missing information about hazards, procedures, equipment, facility, or competence affect evaluation?",
    "CLM-033": "How does WHO evaluate exposure or release likelihood, consequences, and whether laboratory risk can be controlled?",
    "CLM-034": "What risk-based governance and secure-handling topics does WHO's 2024 laboratory biosecurity guidance cover?",
    "CLM-036": "What is the purpose of WHO biological risk assessment and how do its results inform controls, training, and PPE?",
    "CLM-037": "How does WHO define a biological hazard in laboratory biosafety?",
    "CLM-038": "How does WHO define biological risk using likelihood of exposure or release and consequence severity?",
    "CLM-039": "Which procedure, equipment, agent, host, population, and personnel factors affect WHO's laboratory biological risk?",
    "CLM-040": "How should WHO risk controls be selected for a specific activity and checked for residual risk, effectiveness, and sustainability?",
    "CLM-041": "Before laboratory work begins, how does WHO LBM4 say risk assessment should inform activity-specific controls?",
    "CLM-042": "What place does laboratory clothing, gloves, eye protection, and other PPE have within WHO core biosafety requirements?",
    "CLM-043": "When does WHO indicate that respiratory protection may be needed beyond general core PPE requirements?",
    "CLM-044": "Why does WHO not treat PPE alone as sufficient to establish that a laboratory activity is safe?",
    "CLM-045": "What biological hazard, work procedure, equipment, facility, competence, exposure, likelihood, and consequence factors belong in a comprehensive WHO assessment?",
}


def gold(kb):
    claims = {c["claim_id"]: c for c in kb["claims"]}; cases = []
    for cid in sorted(claims):
        c = claims[cid]; spans = c["support_spans"]; common = {"expected_claim_ids": [cid], "expected_document_ids": [c["document_id"]], "expected_source_ids": sorted({s["source_record_id"] for s in spans}), "expected_pages": sorted({s["pdf_page_start"] for s in spans}), "forbidden_claim_ids": [], "forbidden_document_ids": [], "expected_jurisdiction": "International" if c["document_id"].startswith("KB-WHO-") else "Malaysia"}
        cases += [{"case_id": f"C32-P-{cid}", "case_type": "positive", "query": c["text"], **common}, {"case_id": f"C32-Q-{cid}", "case_type": "paraphrase", "query": PARAPHRASES[cid], **common}]
    boundaries = [
        ("WHO-not-Malaysian-law", "Is WHO laboratory biosafety guidance Malaysian law?", [], ["KB-MY-ACT678", "KB-MY-REG2010"]),
        ("handling-not-transport", "Does laboratory handling guidance establish clinical specimen transport requirements?", [], ["KB-MY-TRANSPORT2023"]),
        ("transport-not-containment", "Does a clinical specimen transport guideline establish laboratory containment level?", [], ["KB-MY-CU"]),
        ("generic-GM-not-LMO", "Does generic genetic modification by itself establish LMO status?", [], ["KB-MY-CU"]),
        ("biological-waste-not-SW404", "Is all biological laboratory waste automatically SW 404 scheduled waste?", [], ["KB-MY-SW2005"]),
        ("BSC-not-level", "Does a Class II biological safety cabinet by itself establish the biosafety level?", [], ["KB-MY-CU"]),
        ("Form-E-not-approval", "Does Form E itself constitute approval to begin work?", [], ["KB-MY-FORME"]),
    ]
    for name, query, fc, fd in boundaries:
        cases.append({"case_id": f"C32-B-{name}", "case_type": "boundary_control", "query": query, "expected_claim_ids": [], "expected_document_ids": [], "expected_source_ids": [], "expected_pages": [], "forbidden_claim_ids": fc, "forbidden_document_ids": fd, "expected_jurisdiction": "System"})
    return {"artifact_version": "BioSafe_PhaseC3_2_Gold_Cases_v0.1", "case_count": len(cases), "claim_use_status": STATUS, "live_activation_status": ACTIVATION, "cases": cases}


def run(cls, kb, manifest, dataset):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d); kp=p/"kb.json"; mp=p/"manifest.json"; kp.write_bytes(canonical_bytes(kb)); mp.write_bytes(canonical_bytes(manifest)); r=cls(kp,mp); out=[]
        spans_by_claim = {claim["claim_id"]: claim.get("support_spans", []) for claim in kb["claims"]}
        for case in dataset["cases"]:
            profile, hits = r.retrieve(case["query"], top_k=10); ids=[h["claim_id"] for h in hits]; docs=[h["document_id"] for h in hits]; expected=set(case["expected_claim_ids"]); ranks=[ids.index(x)+1 for x in expected if x in ids]; forbidden_claims=sorted(set(case["forbidden_claim_ids"]) & set(ids[:3])); forbidden_docs=sorted(set(case["forbidden_document_ids"]) & set(docs[:3])); expected_spans=set(case["expected_source_ids"]); retrieved_spans={span["source_record_id"] for hit in hits for span in spans_by_claim.get(hit["claim_id"], [])}; span_completeness=len(expected_spans & retrieved_spans)/len(expected_spans) if expected_spans else 0.0
            route_mismatch=profile.jurisdiction != case["expected_jurisdiction"] and case["case_type"] != "boundary_control"
            failure = "routing" if route_mismatch else ("eligibility" if not hits else ("ranking" if not ranks else "none"))
            out.append({"case_id":case["case_id"],"case_type":case["case_type"],"query_profile":profile.__dict__,"ranked_claim_ids":ids,"ranked_document_ids":docs,"first_relevant_rank":min(ranks) if ranks else None,"forbidden_claims_top3":forbidden_claims,"forbidden_documents_top3":forbidden_docs,"recall_at_10":int(bool(ranks)),"support_span_completeness_at_10":span_completeness,"retrieved_support_span_ids_at_10":sorted(retrieved_spans),"boundary_preserved":not forbidden_claims and not forbidden_docs,"failure_attribution":failure})
        return out


def evaluate():
    mapping=reviewed_crosswalk(); kb,manifest,_=build_artifacts(); dataset=gold(kb); c01,c02,integr,cand01,cand02,candintegr=classes(); runs={"BASE_CFG01":run(c01,kb,manifest,dataset),"BASE_CFG02":run(c02,kb,manifest,dataset),"FROZEN_INTEGRATION_ROUTER":run(integr,kb,manifest,dataset),"C32_CROSSWALK_CFG01":run(cand01,kb,manifest,dataset),"C32_CROSSWALK_CFG02":run(cand02,kb,manifest,dataset),"C32_CROSSWALK_INTEGRATION":run(candintegr,kb,manifest,dataset)}
    summary={}
    for name,rows in runs.items():
        pos=[x for x in rows if x["case_type"] in {"positive","paraphrase"}]; bound=[x for x in rows if x["case_type"]=="boundary_control"]
        summary[name]={"positive_paraphrase_recall_at_10":sum(x["recall_at_10"] for x in pos)/len(pos),"positive_paraphrase_misses":sum(not x["recall_at_10"] for x in pos),"mean_support_span_completeness_at_10":sum(x["support_span_completeness_at_10"] for x in pos)/len(pos),"boundary_preservation_rate":sum(x["boundary_preserved"] for x in bound)/len(bound),"forbidden_claim_top3":sum(bool(x["forbidden_claims_top3"]) for x in bound),"forbidden_document_top3":sum(bool(x["forbidden_documents_top3"]) for x in bound),"failure_attribution":{k:sum(x["failure_attribution"]==k for x in rows) for k in ("routing","eligibility","ranking","none")}}
    hard={name:{"canonical_positive_recall_at_10":all(x["recall_at_10"] for x in rows if x["case_type"]=="positive"),"boundary_controls_preserved":all(x["boundary_preserved"] for x in rows if x["case_type"]=="boundary_control"),"activation_preserved":kb["live_activation_status"]==ACTIVATION and manifest["live_activation_status"]==ACTIVATION and dataset["live_activation_status"]==ACTIVATION} for name,rows in runs.items()}
    return {"artifact_version":"BioSafe_PhaseC3_2_Retrieval_Diagnostics_Report_v0.1","benchmark_mode":"C3_2_GATE_REVIEW_REQUIRED","gate_result":"BLOCKED_PENDING_OWNER_REVIEW","claim_use_status":STATUS,"live_activation_status":ACTIVATION,"input_hashes":{"curated":_hash(CURATED),"crosswalk":_hash(CROSSWALK),"components":_hash(COMPONENTS),"kb":hashlib.sha256(canonical_bytes(kb)).hexdigest(),"gold":hashlib.sha256(canonical_bytes(dataset)).hexdigest()},"crosswalk_mapping":mapping,"summary":summary,"hard_gates":hard,"cases":runs,"gold":dataset}


def artifacts():
    kb,manifest,_=build_artifacts(); return kb,manifest,gold(kb)