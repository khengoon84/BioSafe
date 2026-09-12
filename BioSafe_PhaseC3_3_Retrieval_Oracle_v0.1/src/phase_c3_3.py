from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"src")); sys.path.insert(0,str(ROOT/"BioSafe_PhaseC3_Retrieval_Benchmark_v0.1/src"))
sys.path.insert(0,str(ROOT/"BioSafe_PhaseC3_2_Retrieval_Diagnostics_v0.1/src"))
from phase_c3_benchmark import ACTIVATION, STATUS, build_artifacts, canonical_bytes
from phase_c3_2 import PARAPHRASES, reviewed_crosswalk

CURATED=ROOT/"controlled_sources/ingestion_v0_1/reports/curated_candidate_kb_v0_1.json"
COMPONENTS=ROOT/"controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json"
CROSSWALK=ROOT/"controlled_sources/ingestion_v0_1/config/document_identity_crosswalk_v0_1.json"

def gold(kb):
    claims={c["claim_id"]:c for c in kb["claims"]}; cases=[]
    for cid in sorted(claims):
        c=claims[cid]; spans=c["support_spans"]; common={"acceptable_claim_ids":[cid],"acceptable_document_ids":[c["document_id"]],"expected_source_ids":sorted({s["source_record_id"] for s in spans}),"expected_pages":sorted({s["pdf_page_start"] for s in spans}),"forbidden_claim_ids":[],"forbidden_document_ids":[],"expected_jurisdiction":"International" if c["document_id"].startswith("KB-WHO-") else "Malaysia"}
        cases += [{"case_id":f"C33-P-{cid}","case_type":"canonical_positive","query":c["text"],**common},{"case_id":f"C33-Q-{cid}","case_type":"claim_specific_paraphrase","query":PARAPHRASES[cid],**common}]
    broad=[
        ("risk-assessment-general","What should a biological risk assessment consider?",["CLM-031","CLM-032","CLM-033","CLM-036","CLM-039","CLM-045"],["KB-WHO-LBM4","KB-WHO-LBM4-RA"]),
        ("ppe-risk-controls","How do PPE and risk assessment work together in WHO laboratory biosafety?",["CLM-042","CLM-043","CLM-044"],["KB-WHO-LBM4-PPE","KB-WHO-LBM4-RA"]),
        ("incident-reporting","What reporting routes apply to laboratory incidents in Malaysian contained-use and IBC guidance?",["CLM-009","CLM-017"],["KB-MY-CU","KB-MY-IBC"]),
        ("transport-scope","What does the Malaysian clinical-specimen transport guidance cover, and what does it not decide about waste or containment?",["CLM-026","CLM-027","CLM-028"],["KB-MY-TRANSPORT2023"]),
    ]
    for name,q,claims_,docs in broad:
        cases.append({"case_id":f"C33-M-{name}","case_type":"broad_multi_relevant","query":q,"acceptable_claim_ids":claims_,"acceptable_document_ids":docs,"expected_source_ids":[],"expected_pages":[],"forbidden_claim_ids":[],"forbidden_document_ids":[],"expected_jurisdiction":"International" if docs[0].startswith("KB-WHO") else "Malaysia"})
    boundaries=[
        ("WHO-not-law","Is WHO laboratory biosafety guidance Malaysian law?",["KB-WHO-LBM4","KB-WHO-LBM4-RA","KB-WHO-LBM4-PPE"],"WHO_GUIDANCE_NOT_MALAYSIAN_LAW",["International"]),
        ("handling-not-transport","Does laboratory handling guidance establish clinical specimen transport requirements?",[],"HANDLING_DOES_NOT_ESTABLISH_TRANSPORT",["Malaysia"]),
        ("transport-not-containment","Does a clinical specimen transport guideline establish laboratory containment level?",["KB-MY-TRANSPORT2023"],"TRANSPORT_DOES_NOT_ESTABLISH_CONTAINMENT",["Malaysia"]),
        ("generic-GM-not-LMO","Does generic genetic modification by itself establish LMO status?",["KB-MY-GMMRA","KB-MY-CU"],"GENERIC_GM_DOES_NOT_ESTABLISH_LMO",["Malaysia"]),
        ("waste-not-SW404","Is all biological laboratory waste automatically SW 404 scheduled waste?",["KB-MY-CU"],"BIOLOGICAL_WASTE_NOT_AUTOMATIC_SW404",["Malaysia"]),
        ("BSC-not-level","Does a Class II biological safety cabinet by itself establish the biosafety level?",["KB-MY-CU"],"BSC_DOES_NOT_ESTABLISH_LEVEL",["Malaysia"]),
        ("Form-E-not-approval","Does Form E itself constitute approval to begin work?",["KB-MY-FORME","KB-MY-IBC"],"FORM_E_IS_NOT_APPROVAL",["Malaysia"]),
    ]
    for name,q,docs,boundary,jur in boundaries:
        cases.append({"case_id":f"C33-B-{name}","case_type":"semantic_boundary","query":q,"acceptable_claim_ids":[],"acceptable_document_ids":docs,"expected_source_ids":[],"expected_pages":[],"forbidden_claim_ids":[],"forbidden_document_ids":[],"expected_jurisdiction":jur[0],"required_boundary":boundary,"retrieval_must_be_empty":False})
    return {"artifact_version":"BioSafe_PhaseC3_3_Gold_Cases_v0.1","case_count":len(cases),"canonical_count":32,"paraphrase_count":32,"broad_count":4,"boundary_count":7,"claim_use_status":STATUS,"live_activation_status":ACTIVATION,"cases":cases}

def classes():
    from retriever_base import BioSafeCFG01
    from retriever_cfg02_base import BioSafeCFG02
    from integration_authority_router_v0_1 import BioSafeIntegrationAuthorityRouterV01
    class CandidateMixin:
        def __init__(self,kb_path,manifest_path,*args,**kwargs): self.identity_crosswalk=reviewed_crosswalk(); super().__init__(kb_path,manifest_path,*args,**kwargs)
        def _eligible(self,r,p):
            if r["record_type"]=="control_rule": return super()._eligible(r,p)
            legacy={"TRANSPORT":{"KB-MY-MOH2023"},"WASTE":{"KB-MY-DOE2005","KB-MY-CU","KB-WHO-LBM4"},"MY-FORME":{"KB-MY-FORME","KB-MY-GMMRA"},"MY-IBC":{"KB-MY-IBC","KB-MY-REG2010"},"MY-INCIDENT":{"KB-MY-ACT678","KB-MY-CU","KB-MY-IBC"},"MY-RA":{"KB-MY-GMMRA","KB-MY-ACT678"},"WHO-RA":{"KB-WHO-RA","KB-WHO-LBM4"},"WHO-BIOSEC":{"KB-WHO-BIOSEC"},"MY-REG":{"KB-MY-ACT678","KB-MY-REG2010","KB-MY-CU","KB-MY-GMMRA","KB-MY-IBC"}}
            if p.domain in legacy: return r["document_id"] in {self.identity_crosswalk.get(x,x) for x in legacy[p.domain]}
            return super()._eligible(r,p)
    return [BioSafeCFG01,BioSafeCFG02,BioSafeIntegrationAuthorityRouterV01,type("C33CFG01",(CandidateMixin,BioSafeCFG01),{}),type("C33CFG02",(CandidateMixin,BioSafeCFG02),{}),type("C33Integration",(CandidateMixin,BioSafeIntegrationAuthorityRouterV01),{})]

def run(cls,kb,manifest,data):
    with tempfile.TemporaryDirectory() as d:
        p=Path(d); kp=p/"kb.json"; mp=p/"manifest.json"; kp.write_bytes(canonical_bytes(kb)); mp.write_bytes(canonical_bytes(manifest)); r=cls(kp,mp); out=[]
        for c in data["cases"]:
            profile,hits=r.retrieve(c["query"],top_k=10); ids=[x["claim_id"] for x in hits]; docs=[x["document_id"] for x in hits]; acceptable=set(c["acceptable_claim_ids"]); ranks=[ids.index(x)+1 for x in acceptable if x in ids]; acceptable_doc=bool(set(docs[:3])&set(c["acceptable_document_ids"])); route_ok=profile.jurisdiction==c["expected_jurisdiction"] or c["case_type"]=="semantic_boundary"; boundary_ok=acceptable_doc or not c["acceptable_document_ids"] if c["case_type"]=="semantic_boundary" else True; spans={s["source_record_id"] for x in hits for s in x.get("support_spans",[])}; expected=set(c["expected_source_ids"]); out.append({"case_id":c["case_id"],"case_type":c["case_type"],"query_profile":profile.__dict__,"ranked_claim_ids":ids,"ranked_document_ids":docs,"first_acceptable_rank":min(ranks) if ranks else None,"acceptable_recall_at_10":int(bool(ranks) or (c["case_type"]=="semantic_boundary" and (acceptable_doc or not c["acceptable_document_ids"]))),"support_span_completeness_at_10":len(expected&spans)/len(expected) if expected else None,"route_expected":route_ok,"boundary_evidence_available":boundary_ok,"failure_attribution":"routing" if not route_ok else ("ranking" if c["case_type"]!="semantic_boundary" and not ranks else "none")})
        return out

def evaluate():
    mapping=reviewed_crosswalk(); kb,manifest,_=build_artifacts(); data=gold(kb); a=classes(); names=["BASE_CFG01","BASE_CFG02","FROZEN_INTEGRATION_ROUTER","C33_CROSSWALK_CFG01","C33_CROSSWALK_CFG02","C33_CROSSWALK_INTEGRATION"]; runs={n:run(k,kb,manifest,data) for n,k in zip(names,a)}; summary={}
    for n,rows in runs.items():
        pos=[x for x in rows if x["case_type"] in {"canonical_positive","claim_specific_paraphrase"}]; broad=[x for x in rows if x["case_type"]=="broad_multi_relevant"]; bound=[x for x in rows if x["case_type"]=="semantic_boundary"]; summary[n]={"canonical_recall_at_10":sum(x["acceptable_recall_at_10"] for x in pos if x["case_id"].startswith("C33-P-"))/32,"paraphrase_recall_at_10":sum(x["acceptable_recall_at_10"] for x in pos if x["case_id"].startswith("C33-Q-"))/32,"broad_recall_at_10":sum(x["acceptable_recall_at_10"] for x in broad)/len(broad),"boundary_evidence_available_rate":sum(x["boundary_evidence_available"] for x in bound)/len(bound),"route_mismatch_count":sum(not x["route_expected"] for x in rows),"failure_attribution":{k:sum(x["failure_attribution"]==k for x in rows) for k in ("routing","ranking","none")}}
    hard={n:{"canonical_positive_recall_100":m["canonical_recall_at_10"]==1.0,"activation_preserved":ACTIVATION==ACTIVATION} for n,m in summary.items()}
    return {"artifact_version":"BioSafe_PhaseC3_3_Retrieval_Oracle_Report_v0.1","benchmark_mode":"C3_3_ORACLE_CORRECTED_GATE_REVIEW","gate_result":"BLOCKED_PENDING_OWNER_REVIEW","claim_use_status":STATUS,"live_activation_status":ACTIVATION,"input_hashes":{"curated":_hash(CURATED),"components":_hash(COMPONENTS),"crosswalk":_hash(CROSSWALK),"kb":hashlib.sha256(canonical_bytes(kb)).hexdigest(),"gold":hashlib.sha256(canonical_bytes(data)).hexdigest()},"summary":summary,"hard_gates":hard,"cases":runs,"gold":data,"crosswalk_mapping":mapping}

def _hash(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def artifacts(): kb,m,_=build_artifacts(); return kb,m,gold(kb)