from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
from typing import Any

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

CONFIG = HERE / "data/query_profile_config_v0_1.json"
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

def _load(path: Path) -> Any: return json.loads(path.read_text(encoding="utf-8"))
def _hash(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def cases(kb: dict[str, Any]) -> list[dict[str, Any]]:
    rows=[]
    for claim in sorted(kb["claims"], key=lambda x:x["claim_id"]):
        cid=claim["claim_id"]
        for n,q in enumerate(INDEPENDENT[cid],1):
            expected = "International" if claim["document_id"].startswith("KB-WHO-") else "Malaysia"
            rows.append({"case_id":f"C36-I-{cid}-{n}","case_type":"independent_claim","query":q,"acceptable_claim_ids":[cid],"expected_jurisdiction":expected})
    rows += [
      {"case_id":"C36-U-001","case_type":"unknown_evidence","query":"What exact Malaysian permit exemption applies to an unclassified future organism in a facility not yet described?","acceptable_claim_ids":[],"expected_jurisdiction":"Malaysia"},
      {"case_id":"C36-U-002","case_type":"unknown_evidence","query":"What is the current legal requirement for a jurisdiction not identified by the question?","acceptable_claim_ids":[],"expected_jurisdiction":"Unspecified"},
      {"case_id":"C36-U-003","case_type":"unknown_evidence","query":"Which reviewed source proves that this particular project is safe to start?","acceptable_claim_ids":[],"expected_jurisdiction":"Unspecified"},
      {"case_id":"C36-B-001","case_type":"boundary","query":"Is WHO laboratory biosafety guidance Malaysian law?","acceptable_claim_ids":["CLM-031","CLM-032","CLM-033"],"expected_jurisdiction":"International","required_boundary":"WHO_GUIDANCE_NOT_MALAYSIAN_LAW"},
      {"case_id":"C36-B-002","case_type":"boundary","query":"Does a clinical specimen transport document determine laboratory containment?","acceptable_claim_ids":["CLM-028"],"expected_jurisdiction":"Malaysia","required_boundary":"TRANSPORT_NOT_CONTAINMENT"},
      {"case_id":"C36-B-003","case_type":"boundary","query":"Does Form E itself approve the work?","acceptable_claim_ids":["CLM-025"],"expected_jurisdiction":"Malaysia","required_boundary":"FORM_E_IS_NOT_APPROVAL"},
      {"case_id":"C36-M-001","case_type":"minimal_pair","query":"How does WHO define biological risk?","acceptable_claim_ids":["CLM-038"],"expected_jurisdiction":"International"},
      {"case_id":"C36-M-002","case_type":"minimal_pair","query":"How should a Malaysian contained-use incident be reported?","acceptable_claim_ids":["CLM-009","CLM-017"],"expected_jurisdiction":"Malaysia"},
      {"case_id":"C36-M-003","case_type":"minimal_pair","query":"What packaging is used for a Malaysian clinical specimen?","acceptable_claim_ids":["CLM-026","CLM-027"],"expected_jurisdiction":"Malaysia"},
    ]
    return rows

def _profiles(): return _load(CONFIG)["profiles"]

class ProfileMixin:
    def classify(self, query: str):
        q=query.lower()
        tokens=set(q.replace("-", " ").split())
        config=_load(CONFIG)
        unknown=next(p for p in config["profiles"] if p["id"]=="UNKNOWN")
        explicitly_unknown=any(t in q for t in unknown.get("unknown_terms", []))
        matches=[]
        for p in _profiles():
            if p["id"] == "UNKNOWN": continue
            score=sum(1 for term in p["terms"] if (term in q if " " in term else term in tokens))
            if score: matches.append((score,p))
        if not matches:
            p=unknown
        else:
            # Explicit WHO terminology takes precedence over generic Malaysia
            # terms in authority-boundary questions.
            malaysia=sum(score for score,p in matches if p["jurisdiction"]=="Malaysia")
            international=sum(score for score,p in matches if p["jurisdiction"]=="International")
            # Explicit Malaysia terms win over generic WHO risk terminology;
            # an explicit WHO-vs-law boundary remains international evidence.
            if "malaysian law" in q and "who" in tokens:
                p=next(x for x in _profiles() if x["id"]=="WHO_RISK")
            elif malaysia > international:
                p=max((x for x in matches if x[1]["jurisdiction"]=="Malaysia"),key=lambda x:x[0])[1]
            else:
                p=max(matches,key=lambda x:x[0])[1]
        result=QueryProfile(p["jurisdiction"],p["domain"],p["intent"],"Tier 3" if p["jurisdiction"]=="International" else "Tier 1+2",p["terms"],p["intent"]=="unknown",False)
        result.insufficient_evidence=explicitly_unknown
        return result

class PolicyMixin:
    def __init__(self, kb_path, manifest_path, policy_path, **kwargs):
        self.policy = _load(Path(policy_path))
        self.policy_by_doc = {d["controlled_document_id"]: d for d in self.policy["documents"]}
        if self.policy.get("claim_use_status") != STATUS or self.policy.get("live_activation_status") != ACTIVATION:
            raise ValueError("C3.6 policy safety status invalid")
        super().__init__(kb_path, manifest_path, **kwargs)

    def _eligible(self, record, profile):
        if record["record_type"] == "control_rule": return False
        meta = self.policy_by_doc.get(record["document_id"])
        if not meta or meta.get("retrieval_eligibility") in {"EXCLUDED", "UNREVIEWED"}: return False
        if profile.domain == "UNKNOWN": return False
        return record["jurisdiction"] == profile.jurisdiction or (
            profile.jurisdiction == "Malaysia" and record["jurisdiction"] == "International")

    def retrieve(self, query: str, top_k: int = 5):
        profile=self.classify(query)
        if profile.domain == "UNKNOWN" or getattr(profile,"insufficient_evidence",False):
            return profile, []
        return super().retrieve(query, top_k=top_k)

class C36Mixin:
    def retrieve(self, query: str, top_k: int = 5):
        profile=self.classify(query)
        if profile.domain == "UNKNOWN" or getattr(profile,"insufficient_evidence",False):
            return profile, []
        return super().retrieve(query, top_k=top_k)

class C36CFG01(ProfileMixin, C36Mixin, MetadataMixin, BioSafeCFG01): pass
class C36CFG02(ProfileMixin, C36Mixin, MetadataMixin, BioSafeCFG02): pass

def _fixture(kb, policy):
    claim=_load(FIXTURES/"curated_claim_extension.json"); meta=_load(FIXTURES/"source_policy_extension.json")
    out=json.loads(json.dumps(kb)); out["documents"].append({"document_id":meta["controlled_document_id"],"title":"Synthetic onboarding fixture","authority":"Synthetic fixture","jurisdiction":"International","document_type":"Test fixture","authority_tier":3,"status":"Fixture only","source_url":""}); out["claims"].append({"claim_id":claim["claim_id"],"document_id":claim["controlled_document_id"],"text":claim["text"],"claim_type":claim["claim_type"],"section":"Fixture","page":1,"priority":"test","verification_status":"SYNTHETIC_FIXTURE_ONLY","scope":["training"],"support_spans":claim["support_spans"]})
    pol=json.loads(json.dumps(policy)); pol["documents"].append({"controlled_document_id":meta["controlled_document_id"],"legacy_document_ids":[meta["controlled_document_id"]],"title":"Synthetic onboarding fixture","publisher":"BioSafe tests","jurisdiction":"International","authority_tier":3,"document_type":"Test fixture","publication_date":"","currentness_status":"FIXTURE_ONLY","supersession_status":"FIXTURE_ONLY","allowed_domains":["training"],"excluded_domains":[],"claim_types":["training_record"],"evidence_roles":["synthetic_fixture"],"boundary_tags":[],"source_sha256":meta["source_sha256"],"curated_claim_count":1})
    return out,pol,{"case_id":"C36-F-001","case_type":"new_document_fixture","query":"Which source describes a documented biosafety training record?","acceptable_claim_ids":[claim["claim_id"]],"expected_jurisdiction":"International"}

def _run(cls,kb,manifest,policy,rows,metadata_layer=True):
    with tempfile.TemporaryDirectory() as td:
        p=Path(td); kp=p/"kb.json"; mp=p/"manifest.json"; pp=p/"policy.json"; kp.write_bytes(canonical_bytes(kb)); mp.write_bytes(canonical_bytes(manifest)); pp.write_bytes(canonical_bytes(policy)); r=cls(kp,mp,policy_path=pp,metadata_layer=metadata_layer); result=[]
        for c in rows:
            profile,hits=r.retrieve(c["query"],top_k=10); ids=[h["claim_id"] for h in hits]; accepted=bool(set(ids)&set(c["acceptable_claim_ids"])); unknown_ok=c["case_type"]!="unknown_evidence" or not hits; target=[h for h in hits if h["claim_id"] in c["acceptable_claim_ids"]]; spans={s["source_record_id"] for h in target for s in h.get("support_spans",[])}; expected=set(c.get("expected_source_ids",[])); span_complete=(len(spans & expected)/len(expected)) if expected else (all(h.get("support_spans") for h in target) if c["case_type"] not in {"unknown_evidence","boundary"} else True); boundary_map={"WHO_GUIDANCE_NOT_MALAYSIAN_LAW":"WHO_GUIDANCE_NOT_MALAYSIAN_LAW","TRANSPORT_NOT_CONTAINMENT":"TRANSPORT_SCOPE_LIMITATION","FORM_E_IS_NOT_APPROVAL":"NOT_APPROVAL_OR_AUTHORIZATION"}; needed=boundary_map.get(c.get("required_boundary"),""); policy_tags={d["controlled_document_id"]:set(d.get("boundary_tags",[])) for d in policy["documents"]}; boundary_ok=c["case_type"]!="boundary" or any(needed in policy_tags.get(h["document_id"],set()) for h in hits); metadata_scores=[h.get("metadata_score",0.0) for h in hits]; result.append({"case_id":c["case_id"],"case_type":c["case_type"],"ranked_claim_ids":ids,"query_profile":profile.__dict__,"first_acceptable_rank":next((ids.index(x)+1 for x in c["acceptable_claim_ids"] if x in ids),None),"recall_at_10":int(accepted),"route_ok":profile.jurisdiction==c["expected_jurisdiction"],"unknown_fail_closed":unknown_ok,"support_span_complete":span_complete,"boundary_preserved":boundary_ok,"metadata_score_present":any("metadata_score" in h for h in hits),"metadata_score_max":max(metadata_scores,default=0.0)})
        return result

def evaluate():
    kb,manifest,_=build_artifacts(); policy=build_artifact(); base=cases(kb); fkb,fpol,fc=_fixture(kb,policy); rows=base+[fc]; runs={}
    for name,cls in (("C36_METADATA_CFG01",C36CFG01),("C36_METADATA_CFG02",C36CFG02)):
        runs[name]={"metadata_on":_run(cls,fkb,manifest,fpol,rows,True),"metadata_off":_run(cls,fkb,manifest,fpol,rows,False)}
    summary={}
    for name,modes in runs.items():
        on=modes["metadata_on"]; ind=[x for x in on if x["case_type"]=="independent_claim"]; unk=[x for x in on if x["case_type"]=="unknown_evidence"]; fix=[x for x in on if x["case_type"]=="new_document_fixture"]; bound=[x for x in on if x["case_type"]=="boundary"]; summary[name]={"independent_recall_at_10":sum(x["recall_at_10"] for x in ind)/len(ind),"independent_route_accuracy":sum(x["route_ok"] for x in ind)/len(ind),"unknown_fail_closed_rate":sum(x["unknown_fail_closed"] for x in unk)/len(unk),"boundary_preservation_rate":sum(x["boundary_preserved"] for x in bound)/len(bound),"new_document_recall_at_10":fix[0]["recall_at_10"],"metadata_changed_rankings":modes["metadata_on"]!=modes["metadata_off"],"hard_gates":{"canonical_independent_coverage":all(x["recall_at_10"] for x in ind),"unknown_fail_closed":all(x["unknown_fail_closed"] for x in unk),"boundary_preserved":all(x["boundary_preserved"] for x in bound),"fixture_onboarding":bool(fix[0]["recall_at_10"])}}
    return {"artifact_version":"BioSafe_PhaseC3_6_Retrieval_Correction_Report_v0.1","benchmark_mode":"C3_6_RETRIEVAL_CORRECTION_GATE_REVIEW","gate_result":"BLOCKED_PENDING_OWNER_REVIEW","claim_use_status":STATUS,"live_activation_status":ACTIVATION,"case_count":len(rows),"input_hashes":{"query_profile_config":_hash(CONFIG),"fixture_claim":_hash(FIXTURES/"curated_claim_extension.json"),"fixture_source":_hash(FIXTURES/"source.txt")},"summary":summary,"cases":runs}

def artifacts():
    kb,manifest,_=build_artifacts(); policy=build_artifact(); return policy,{"cases":cases(kb)}