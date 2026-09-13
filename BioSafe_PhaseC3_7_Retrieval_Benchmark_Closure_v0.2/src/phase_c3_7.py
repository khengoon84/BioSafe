from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
from typing import Any
from contracts import BenchmarkCase, CaseResult, VALID_METRICS
from metrics import metadata_comparison, summarize

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "BioSafe_PhaseC3_Retrieval_Benchmark_v0.1/src"))
sys.path.insert(0, str(ROOT / "BioSafe_PhaseC3_4_Metadata_Generalization_v0.1/scripts"))
sys.path.insert(0, str(ROOT / "BioSafe_PhaseC3_4_Metadata_Generalization_v0.1/src"))
from retriever_base import BioSafeCFG01, QueryProfile
from retriever_cfg02_base import BioSafeCFG02
from phase_c3_benchmark import ACTIVATION, STATUS, build_artifacts, canonical_bytes
from build_retrieval_policy import build_artifact
from phase_c3_4 import MetadataMixin

CONFIG = HERE / "data/query_profile_config_v0_2.json"
BOUNDARIES = HERE / "data/boundary_contracts_v0_2.json"
FIXTURES = HERE / "fixtures"

INDEPENDENT = {
"CLM-008": ["Which Malaysian contained-use examples combine GM-BSL2 access, training, decontamination and incident controls?", "For LMO work at GM-BSL2, what practical laboratory safeguards are described?"],
"CLM-009": ["After a GM-BSL2 spill, which local people or bodies should receive an immediate report?", "What response and escalation arrangements apply when contained-use work causes an over-exposure risk?"],
"CLM-010": ["What primary-containment equipment is identified for aerosol-generating contained-use work?", "Which cabinet is associated with respiratory exposure risk in the Malaysian contained-use material?"],
"CLM-011": ["Which subjects are included in the Malaysian contained-use guidance, from waste through facilities?", "Does the contained-use source address treatment, storage, transfer and disposal as well as handling?"],
"CLM-012": ["For a Malaysian GMM assessment, which hazards and possible releases are considered?", "How does the Malaysian microorganism guidance connect risk assessment with BSL and human, animal, plant and environmental effects?"],
"CLM-013": ["What makes a GMM risk submission sufficiently informative for reviewers when uncertainty remains?", "How should missing background or unresolved hazards be handled in the risk assessment?"],
"CLM-014": ["When should a GMM risk assessment be revisited rather than left unchanged?", "Is the Malaysian risk assessment treated as a one-off exercise or something updated when circumstances change?"],
"CLM-015": ["What does a Malaysian IBC examine about facilities, procedures and staff competence?", "Which oversight tasks are assigned to the institutional biosafety committee?"],
"CLM-016": ["What is the principal investigator's accountability to the IBC under the Malaysian source?", "Who must comply with applicable biosafety requirements in relation to the IBC?"],
"CLM-017": ["What reporting timing and route does Malaysian IBC material give for incidents or occupational exposure?", "Where should a contained-use incident be reported according to the IBC source?"],
"CLM-021": ["Which human-health and accidental-release issues does Malaysia's Form E risk section ask applicants to address?", "What risk dimensions are requested in Form E for the proposed activity and an unintended release?"],
"CLM-022": ["What does Form E ask about off-site movement, cleanup, protection and contingency arrangements?", "Which transport, decontamination and disposal precautions appear in the Form E risk-management fields?"],
"CLM-023": ["Which premises and laboratory details are requested in Form E, including BSL and inspection information?", "What facility and biosafety-officer information does the Form E section seek?"],
"CLM-024": ["How can confidential business information be identified in Form E?", "What does the Malaysian form say about claiming confidentiality for business information?"],
"CLM-025": ["Who completes the IBC Assessment Report, and is it a field for the researcher?", "Is the IBC Assessment Report something the PI fills in for BioSafe's scoring?"],
"CLM-026": ["What does Malaysia's health-ministry guidance cover when sending clinical samples or infectious substances?", "Which specimen classification and package-marking topics are within the 2023 Malaysian transport guidance?"],
"CLM-027": ["How should a clinical sample be packaged for transport under the Malaysian guidance, including Category A or B distinctions?", "What three-layer packaging approach and P620/P650 contexts are described for infectious substances?"],
"CLM-028": ["Does the Malaysian specimen-transport document also decide clinical-waste rules or laboratory containment?", "What important subjects fall outside the scope of the clinical-specimen transport guideline?"],
"CLM-031": ["How does WHO LBM4 balance precautions against the work being performed?", "What general evidence-led approach does WHO use when selecting laboratory biosafety measures?"],
"CLM-032": ["Which facts about the agent, procedure, facility and people are needed for a laboratory risk assessment?", "What information should be assembled before evaluating biological risk in a WHO laboratory setting?"],
"CLM-033": ["How does WHO evaluate the chance and consequences of exposure or release?", "What questions about likelihood, consequences and residual risk belong in WHO risk evaluation?"],
"CLM-034": ["What risk-and-evidence approach does WHO apply to laboratory biosecurity and high-consequence work?", "Which levels of oversight and lifecycle activities are covered by the WHO biosecurity guidance?"],
"CLM-036": ["What is the purpose of carrying out a biological risk assessment according to WHO?", "How does WHO describe the process of collecting information and evaluating laboratory risk?"],
"CLM-037": ["In WHO laboratory terminology, what makes a biological agent a hazard?", "How is biological hazard described in the WHO biosafety material?"],
"CLM-038": ["In a laboratory context, how does WHO define biological risk?", "What two ideas are combined in WHO's definition of biological risk?"],
"CLM-039": ["Which changing features of an activity can alter laboratory biological risk?", "Why does WHO say procedure, equipment and context can change the risk?"],
"CLM-040": ["How should control measures be chosen and checked for a particular laboratory activity under WHO's framework?", "What does WHO require after selecting activity-specific risk controls?"],
"CLM-041": ["Why does WHO use a risk-based approach instead of one fixed control package for every activity?", "How are laboratory safeguards matched to the specific work in WHO LBM4?"],
"CLM-042": ["Where does PPE fit within WHO's broader laboratory biosafety requirements?", "Does WHO treat protective clothing and equipment as the whole biosafety programme?"],
"CLM-043": ["When might respiratory protection be selected on the basis of laboratory risk?", "Which PPE needs does WHO say depend on the assessed exposure risk?"],
"CLM-044": ["Why cannot PPE alone demonstrate that a laboratory activity is safe under WHO's framework?", "What other controls must be considered alongside PPE in a WHO risk assessment?"],
"CLM-045": ["What elements besides the organism itself belong in a comprehensive WHO biological risk assessment?", "How should work practices, people, equipment and facility context be combined when assessing risk?"],
}

def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _explicit_jurisdiction(query: str) -> str:
    lower=query.lower()
    if any(x in lower for x in ("malaysia", "malaysian", "ministry of health", "form e", "gmm", "lmo", "ibc", "gm-bsl")):
        return "Malaysia"
    if "WHO" in query or "World Health Organization" in query or "WHO's" in query:
        return "International"
    return "Unspecified"


def cases(kb: dict[str, Any]) -> list[dict[str, Any]]:
    claims={c["claim_id"]:c for c in kb["claims"]}; rows=[]
    for claim in sorted(kb["claims"], key=lambda x:x["claim_id"]):
        cid=claim["claim_id"]
        for n,query in enumerate(INDEPENDENT[cid],1):
            rows.append({"case_id":f"C37-I-{cid}-{n}", "case_type":"independent_claim", "query":query,
                "acceptable_claim_ids":[cid], "acceptable_document_ids":[claim["document_id"]],
                "expected_jurisdiction":_explicit_jurisdiction(query),
                "expected_source_record_ids":sorted({s["source_record_id"] for s in claim["support_spans"]}),
                "metrics":["retrieval","route","support_span","leakage","diversity","duplicates"], "partition":"development"})
    boundaries=[
      ("WHO_NOT_LAW","Is WHO laboratory biosafety guidance Malaysian law?",["CLM-031","CLM-032","CLM-033"],"International","WHO_GUIDANCE_NOT_MALAYSIAN_LAW"),
      ("HANDLING_NOT_TRANSPORT","Does Malaysian contained-use handling guidance establish clinical specimen transport requirements?",["CLM-011"],"Malaysia","HANDLING_DOES_NOT_ESTABLISH_TRANSPORT"),
      ("TRANSPORT_NOT_CONTAINMENT","Does a Malaysian clinical specimen transport document determine laboratory containment?",["CLM-028"],"Malaysia","TRANSPORT_DOES_NOT_ESTABLISH_CONTAINMENT"),
      ("GM_NOT_LMO","Does Malaysian generic genetic modification by itself establish LMO status?",["CLM-012"],"Malaysia","GENERIC_GM_DOES_NOT_ESTABLISH_LMO"),
      ("WASTE_NOT_SW404","Is all Malaysian biological laboratory waste automatically SW 404 scheduled waste?",["CLM-011"],"Malaysia","BIOLOGICAL_WASTE_NOT_AUTOMATIC_SW404"),
      ("BSC_NOT_LEVEL","Does a Class II biological safety cabinet by itself establish the Malaysian biosafety level?",["CLM-010"],"Malaysia","BSC_DOES_NOT_ESTABLISH_LEVEL"),
      ("FORM_E_NOT_APPROVAL","Does Malaysia's Form E itself approve the work?",["CLM-025"],"Malaysia","FORM_E_IS_NOT_APPROVAL"),
    ]
    for name,query,ids,jurisdiction,boundary in boundaries:
        docs=sorted({claims[x]["document_id"] for x in ids}); spans=[]
        rows.append({"case_id":f"C37-B-{name}","case_type":"boundary","query":query,"acceptable_claim_ids":ids,"acceptable_document_ids":docs,"expected_jurisdiction":jurisdiction,"expected_source_record_ids":spans,"required_boundary":boundary,"metrics":["retrieval","route","boundary","support_span","leakage"]})
    rows += [
      {"case_id":"C37-U-001","case_type":"unknown_evidence","query":"What exact Malaysian permit exemption applies to an unclassified future organism in a facility not yet described?","acceptable_claim_ids":[],"acceptable_document_ids":[],"expected_jurisdiction":"Malaysia","retrieval_must_be_empty":True,"metrics":["unknown"]},
      {"case_id":"C37-U-002","case_type":"currentness","query":"What is the current legal requirement for a jurisdiction not identified by the question?","acceptable_claim_ids":[],"acceptable_document_ids":[],"expected_jurisdiction":"Unspecified","retrieval_must_be_empty":True,"metrics":["unknown","currentness"]},
      {"case_id":"C37-U-003","case_type":"unknown_evidence","query":"Which reviewed source proves that this particular project is safe to start?","acceptable_claim_ids":[],"acceptable_document_ids":[],"expected_jurisdiction":"Unspecified","retrieval_must_be_empty":True,"metrics":["unknown"]},
      {"case_id":"C37-C-001","case_type":"conflict","query":"Two unverified sources conflict about whether an unidentified project needs approval; decide which is legally correct.","acceptable_claim_ids":[],"acceptable_document_ids":[],"expected_jurisdiction":"Unspecified","retrieval_must_be_empty":True,"metrics":["unknown","conflict"]},
      {"case_id":"C37-M-001","case_type":"minimal_pair","query":"How does WHO define biological risk?","acceptable_claim_ids":["CLM-038"],"acceptable_document_ids":[claims["CLM-038"]["document_id"]],"expected_jurisdiction":"International","expected_source_record_ids":[s["source_record_id"] for s in claims["CLM-038"]["support_spans"]],"metrics":["retrieval","route","support_span"]},
      {"case_id":"C37-M-002","case_type":"minimal_pair","query":"How should a Malaysian contained-use incident be reported?","acceptable_claim_ids":["CLM-009","CLM-017"],"acceptable_document_ids":[claims["CLM-009"]["document_id"],claims["CLM-017"]["document_id"]],"expected_jurisdiction":"Malaysia","expected_source_record_ids":[],"metrics":["retrieval","route"]},
      {"case_id":"C37-M-003","case_type":"minimal_pair","query":"What packaging is used for a Malaysian clinical specimen?","acceptable_claim_ids":["CLM-026","CLM-027"],"acceptable_document_ids":[claims["CLM-026"]["document_id"]],"expected_jurisdiction":"Malaysia","expected_source_record_ids":[],"metrics":["retrieval","route"]},
    ]
    return rows


class ProfileMixin:
    def classify(self, query: str):
        lower=query.lower(); config=_load(CONFIG)
        unknown=next(p for p in config["profiles"] if p["id"]=="UNKNOWN")
        explicitly_unknown=any(term in lower for term in unknown["unknown_terms"])
        explicit_who=("WHO" in query or "World Health Organization" in query or "WHO's" in query)
        malaysia_terms=("malaysia","malaysian","ministry of health","form e","gmm","lmo","ibc","gm-bsl")
        explicit_malaysia=any(term in lower for term in malaysia_terms)
        if explicitly_unknown:
            jurisdiction=_explicit_jurisdiction(query); domain="UNKNOWN"; intent="unknown"; scope=[]
        elif explicit_who and not ("malaysian law" in lower):
            jurisdiction="International"
            if "biosecurity" in lower:
                domain="WHO-BIOSEC"; intent="biosecurity"; scope=["biosecurity","governance","lifecycle"]
            elif any(term in lower for term in ("ppe","personal protective","respiratory protection")):
                domain="WHO-PPE"; intent="ppe"; scope=["ppe","respiratory protection","risk controls"]
            else:
                domain="WHO-RA"; intent="risk_assessment"; scope=["who","risk assessment","biosafety"]
        elif explicit_who and "malaysian law" in lower:
            jurisdiction="International"; domain="WHO-RA"; intent="authority_boundary"; scope=["who","malaysian law"]
        elif explicit_malaysia:
            jurisdiction="Malaysia"
            if "contained-use handling" in lower or "contained use handling" in lower:
                domain="MY-REG"; intent="scope_boundary"; scope=["contained use","handling","transport boundary"]
            elif "form e" in lower or "ibc assessment report" in lower:
                domain="MY-FORME"; intent="scope_gate" if ("approve" in lower or "ibc assessment report" in lower) else "Form E"; scope=["form e","ibc boundary"]
            elif any(term in lower for term in ("clinical specimen","clinical-specimen","specimen-transport","infectious substance","packag","transport guideline")):
                domain="TRANSPORT"; intent="transport"; scope=["clinical specimen","infectious substance","transport"]
            elif any(term in lower for term in ("scheduled waste","sw 404")):
                domain="WASTE"; intent="waste"; scope=["scheduled waste","sw 404"]
            else:
                domain="MY-REG"; intent="contained_use"; scope=["lmo","gmm","contained use","form e","ibc","risk assessment"]
        elif any(term in lower for term in ("documented biosafety training","training record","training documentation")):
            jurisdiction="International"; domain="training"; intent="training_record"; scope=["training record"]
        else:
            jurisdiction="Unspecified"; domain="GENERAL"; intent="educational"; scope=[]
        result=QueryProfile(jurisdiction,domain,intent,"Tier 3" if jurisdiction=="International" else "Tier 1+2",scope,domain=="UNKNOWN",False)
        result.insufficient_evidence=explicitly_unknown
        return result

class PolicyMixin:
    def _eligible(self, record, profile):
        if record["record_type"] == "control_rule": return False
        meta = self.policy_by_doc.get(record["document_id"])
        if not meta or meta.get("retrieval_eligibility") in {"EXCLUDED", "UNREVIEWED"}: return False
        if profile.domain == "UNKNOWN": return False
        if profile.jurisdiction == "Unspecified": return True
        return record["jurisdiction"] == profile.jurisdiction or (
            profile.jurisdiction == "Malaysia" and record["jurisdiction"] == "International")

    def _authority_score(self, record, profile):
        if profile.jurisdiction == "Unspecified":
            return 1.0
        return super()._authority_score(record, profile)

    def retrieve(self, query: str, top_k: int = 5):
        profile=self.classify(query)
        if profile.domain == "UNKNOWN" or getattr(profile,"insufficient_evidence",False):
            return profile, []
        return super().retrieve(query, top_k=top_k)

class C37Mixin:
    def _eligible(self, record, profile):
        if record["record_type"] == "control_rule":
            return False
        meta=self.policy_by_doc.get(record["document_id"])
        if not meta or not meta.get("source_sha256") or meta.get("retrieval_eligibility") in {"EXCLUDED","UNREVIEWED"}:
            return False
        if profile.domain == "UNKNOWN":
            return False
        document_id=record["document_id"]
        domain_documents={
            "MY-FORME":{"KB-MY-FORME","KB-MY-GMMRA"},
            "TRANSPORT":{"KB-MY-TRANSPORT2023"},
            "WASTE":{"KB-MY-SW2005","KB-MY-CU"},
            "MY-REG":{"KB-MY-CU","KB-MY-FORME","KB-MY-GMMRA","KB-MY-IBC","KB-MY-TRANSPORT2023"},
            "WHO-RA":{"KB-WHO-LBM4","KB-WHO-LBM4-RA","KB-WHO-LBM4-PPE"},
            "WHO-PPE":{"KB-WHO-LBM4","KB-WHO-LBM4-PPE","KB-WHO-LBM4-RA"},
            "WHO-BIOSEC":{"KB-WHO-BIOSEC"},
        }
        if profile.domain in domain_documents:
            return document_id in domain_documents[profile.domain]
        if profile.jurisdiction == "Unspecified":
            return True
        return record["jurisdiction"] == profile.jurisdiction or (profile.jurisdiction == "Malaysia" and record["jurisdiction"] == "International")

    def retrieve(self, query: str, top_k: int = 5):
        profile=self.classify(query)
        if profile.domain == "UNKNOWN" or getattr(profile,"insufficient_evidence",False):
            return profile, []
        return super().retrieve(query, top_k=top_k)

class C37CFG01(ProfileMixin, C37Mixin, MetadataMixin, PolicyMixin, BioSafeCFG01): pass
class C37CFG02(ProfileMixin, C37Mixin, MetadataMixin, PolicyMixin, BioSafeCFG02): pass

def _fixture(kb, policy):
    claim=_load(FIXTURES/"curated_claim_extension.json"); meta=_load(FIXTURES/"source_policy_extension.json")
    out=json.loads(json.dumps(kb)); out["documents"].append({"document_id":meta["controlled_document_id"],"title":"Synthetic onboarding fixture","authority":"Synthetic fixture","jurisdiction":"International","document_type":"Test fixture","authority_tier":3,"status":"Fixture only","source_url":""}); out["claims"].append({"claim_id":claim["claim_id"],"document_id":claim["controlled_document_id"],"text":claim["text"],"claim_type":claim["claim_type"],"section":"Fixture","page":1,"priority":"test","verification_status":"SYNTHETIC_FIXTURE_ONLY","scope":["training"],"support_spans":claim["support_spans"]})
    pol=json.loads(json.dumps(policy)); pol["documents"].append({"controlled_document_id":meta["controlled_document_id"],"legacy_document_ids":[meta["controlled_document_id"]],"title":"Synthetic onboarding fixture","publisher":"BioSafe tests","jurisdiction":"International","authority_tier":3,"document_type":"Test fixture","publication_date":"","currentness_status":"FIXTURE_ONLY","supersession_status":"FIXTURE_ONLY","allowed_domains":["training"],"excluded_domains":[],"claim_types":["training_record"],"evidence_roles":["synthetic_fixture"],"boundary_tags":[],"source_sha256":meta["source_sha256"],"curated_claim_count":1})
    return out,pol,{"case_id":"C37-F-001","case_type":"new_document_fixture","query":"Which source describes a documented biosafety training record?","acceptable_claim_ids":[claim["claim_id"]],"acceptable_document_ids":[claim["controlled_document_id"]],"expected_jurisdiction":"International","expected_source_record_ids":[s["source_record_id"] for s in claim["support_spans"]],"metrics":["retrieval","route","support_span"]}

def validate_cases(rows: list[BenchmarkCase], kb: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    errors=[]; claims={c["claim_id"]:c for c in kb["claims"]}; docs={d["controlled_document_id"] for d in policy["documents"]}
    spans={s["source_record_id"] for c in kb["claims"] for s in c.get("support_spans",[])}
    boundary_contracts=_load(BOUNDARIES)["contracts"]
    if len({c.case_id for c in rows}) != len(rows): errors.append("duplicate case_id")
    if len({c.query for c in rows}) != len(rows): errors.append("duplicate query")
    for case in rows:
        unknown_metrics=case.metrics-VALID_METRICS
        if unknown_metrics: errors.append(f"{case.case_id}: unknown metrics {sorted(unknown_metrics)}")
        if "retrieval" in case.metrics and not case.acceptable_claim_ids: errors.append(f"{case.case_id}: retrieval metric lacks acceptable claims")
        for cid in case.acceptable_claim_ids:
            if cid not in claims: errors.append(f"{case.case_id}: missing claim {cid}")
        for did in case.acceptable_document_ids:
            if did not in docs and not did.startswith("FIXTURE-"): errors.append(f"{case.case_id}: missing document {did}")
        for sid in case.expected_source_record_ids:
            if sid not in spans and not sid.startswith("FIXTURE-"): errors.append(f"{case.case_id}: missing source span {sid}")
        if "boundary" in case.metrics and case.required_boundary not in boundary_contracts: errors.append(f"{case.case_id}: undefined boundary {case.required_boundary}")
    return errors


def _run(cls,kb,manifest,policy,cases_,metadata_layer=True):
    claim_map={c["claim_id"]:c for c in kb["claims"]}; policy_map={d["controlled_document_id"]:d for d in policy["documents"]}
    boundary_contracts=_load(BOUNDARIES)["contracts"]
    with tempfile.TemporaryDirectory() as td:
        p=Path(td); kp=p/"kb.json"; mp=p/"manifest.json"; pp=p/"policy.json"
        kp.write_bytes(canonical_bytes(kb)); mp.write_bytes(canonical_bytes(manifest)); pp.write_bytes(canonical_bytes(policy))
        retriever=cls(kp,mp,policy_path=pp,metadata_layer=metadata_layer); results=[]
        for case in cases_:
            profile,hits=retriever.retrieve(case.query,top_k=10); ids=[h["claim_id"] for h in hits]; docs=[h["document_id"] for h in hits]
            ranks=[ids.index(cid)+1 for cid in case.acceptable_claim_ids if cid in ids]; accepted=bool(ranks)
            target_ids={cid for cid in ids if cid in case.acceptable_claim_ids}
            actual_spans={s["source_record_id"] for cid in target_ids for s in claim_map[cid].get("support_spans",[])}
            expected=set(case.expected_source_record_ids)
            if "support_span" not in case.metrics: span_status="NOT_APPLICABLE"
            elif not accepted: span_status="NO_ACCEPTABLE_HIT"
            elif expected <= actual_spans: span_status="COMPLETE"
            elif expected & actual_spans: span_status="PARTIAL"
            else: span_status="MISSING"
            relevant_docs={claim_map[cid]["document_id"] for cid in target_ids}
            boundary_ok=None
            if "boundary" in case.metrics:
                tagged=any(did in boundary_contracts[case.required_boundary] for did in relevant_docs)
                boundary_ok=accepted and tagged and not bool(set(docs)&set(case.forbidden_document_ids))
            empty_ok=not hits
            route_ok=profile.jurisdiction==case.expected_jurisdiction if "route" in case.metrics else None
            retrieval_ok=(empty_ok if case.retrieval_must_be_empty else accepted) if ("retrieval" in case.metrics or case.retrieval_must_be_empty) else None
            result=CaseResult(case.case_id,case.case_type,case.partition,ids,docs,profile.__dict__,route_ok,retrieval_ok,empty_ok if "unknown" in case.metrics else None,boundary_ok,empty_ok if "currentness" in case.metrics else None,empty_ok if "conflict" in case.metrics else None,span_status,min(ranks) if ranks else None,{str(k):int(any(rank<=k for rank in ranks)) for k in (1,3,5,10)},len(expected&actual_spans)/len(expected) if expected else None,sum(1 for h in hits if profile.jurisdiction not in {"Unspecified","System"} and h["jurisdiction"]!=profile.jurisdiction),len(set(docs)),max((docs.count(d) for d in set(docs)),default=0)/len(docs) if docs else 0.0,any("metadata_score" in h for h in hits))
            results.append(result)
        return results


def evaluate():
    kb,manifest,_=build_artifacts(); policy=retrieval_policy(); fkb,fpol,fixture=_fixture(kb,policy)
    raw=cases(kb)+[fixture]; typed=[BenchmarkCase.from_dict(row) for row in raw]; errors=validate_cases(typed,fkb,fpol)
    common={"artifact_version":"BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_Report_v0.2","benchmark_mode":"C3_7_RETRIEVAL_BENCHMARK_CLOSURE_V0_2","gate_result":"BLOCKED_CORRECTION_REQUIRED" if errors else "BLOCKED_PENDING_OWNER_REVIEW","claim_use_status":STATUS,"live_activation_status":ACTIVATION,"case_count":len(typed),"artifact_validation_errors":errors,"input_hashes":{"query_profile_config":_hash(CONFIG),"boundary_contracts":_hash(BOUNDARIES),"fixture_claim":_hash(FIXTURES/"curated_claim_extension.json"),"fixture_source":_hash(FIXTURES/"source.txt")}}
    if errors: return {**common,"machine_gate_result":"INVALID_BENCHMARK_ARTIFACT","summary":{},"cases":{}}
    runs={}; summary={}
    for name,cls in (("C37_METADATA_CFG01",C37CFG01),("C37_METADATA_CFG02",C37CFG02)):
        on=_run(cls,fkb,manifest,fpol,typed,True); off=_run(cls,fkb,manifest,fpol,typed,False)
        runs[name]={"metadata_on":[r.as_dict() for r in on],"metadata_off":[r.as_dict() for r in off]}
        comparison=metadata_comparison(on,off)
        summary[name]={"metadata_on":summarize(on),"metadata_off":summarize(off),"metadata_comparison":comparison,
            "metadata_on_candidate_eligible":all(summarize(on)["hard_gates"].values()) and not comparison["rank_harmed_case_ids"],
            "metadata_off_candidate_eligible":all(summarize(off)["hard_gates"].values())}
    eligible=[f"{name}:{mode}" for name,s in summary.items() for mode in ("metadata_on","metadata_off") if s[f"{mode}_candidate_eligible"]]
    return {**common,"machine_gate_result":"BLOCKED_HOLDOUT_AND_OWNER_REVIEW" if eligible else "FAIL_RETRIEVAL_GATE","eligible_development_candidates":eligible,"summary":summary,"cases":runs,"limitations":["Finite development fixture; an independently authored locked holdout remains required.","Metadata-on is not eligible when any measured rank is harmed.","No Ollama or live runtime validation was performed.","Owner semantic and provenance review remains required."]}

def artifacts():
    kb,manifest,_=build_artifacts(); policy=retrieval_policy(); rows=cases(kb)
    return policy,{"artifact_version":"BioSafe_PhaseC3_7_Gold_Cases_v0.2","case_count":len(rows),"claim_use_status":STATUS,"live_activation_status":ACTIVATION,"cases":rows}


def retrieval_policy():
    policy=build_artifact()
    policy["artifact_version"]="BioSafe_PhaseC3_7_Retrieval_Policy_v0.2"
    return policy