from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from c5_bridge import enrich


class CandidatePipelineV01:
    """Build the frozen pipeline message contract from the reviewed C3 candidate."""

    def __init__(self, root: Path, kb: dict[str, Any], manifest: dict[str, Any], policy: dict[str, Any], retriever: Any, top_k: int = 3):
        self.root=Path(root); self.kb=kb; self.manifest=manifest; self.policy=policy; self.retriever=retriever; self.top_k=top_k
        self.system_prompt=(self.root/"prompts/system_prompt_v0.1.txt").read_text(encoding="utf-8")
        self.response_schema=json.loads((self.root/"prompts/response_schema_v0.1.json").read_text(encoding="utf-8"))
        self.claims={c["claim_id"]:c for c in kb["claims"]}

    def retrieve(self, query: str):
        profile,hits=self.retriever.retrieve(query,self.top_k)
        evidence=[enrich(hit,self.claims[hit["claim_id"]],self.policy,"C5_REVIEWED_CANDIDATE","C37_METADATA_CFG02:metadata_off") for hit in hits if hit["claim_id"] in self.claims]
        return profile,evidence

    @staticmethod
    def _evidence_item(row: dict[str, Any]) -> dict[str, Any]:
        return {"evidence_id":row["record_id"],"record_type":row["record_type"],"document_id":row["document_id"],"title":row["title"],"authority":row["authority"],"jurisdiction":row["jurisdiction"],"section":row.get("section",""),"page":row.get("page",""),"claim_type":row.get("claim_type",""),"text":row.get("text",""),"source_url":row.get("source_url",""),"must_cite":row.get("must_cite",False),"retrieval_score":row.get("final_score"),"support_spans":row.get("support_spans",[]),"source_sha256":row.get("source_sha256"),"verification_status":row.get("verification_status"),"evidence_origin":row.get("evidence_origin"),"candidate_path_id":row.get("candidate_path_id")}

    def build_bundle(self, query: str, case_id: str | None = None, safety_class: str | None = None):
        profile,evidence=self.retrieve(query)
        route={"jurisdiction":profile.jurisdiction,"domain":profile.domain,"intent":profile.intent,"preferred_tier":profile.preferred_tier,"scope":profile.scope,"uncertainty_sensitive":profile.uncertainty_sensitive,"safety_sensitive":profile.safety_sensitive}
        return {"case_id":case_id,"user_query":query,"input_safety_class":safety_class,"route":route,"evidence_bundle":[self._evidence_item(row) for row in evidence],"response_schema":self.response_schema,"candidate_path_id":"C37_METADATA_CFG02:metadata_off","evidence_origin":"C5_REVIEWED_CANDIDATE"}

    def build_messages(self, query: str, case_id: str | None = None, safety_class: str | None = None):
        bundle=self.build_bundle(query,case_id,safety_class)
        payload={"task":"Answer the user query using only the supplied evidence and BioSafe policy.","case_id":case_id,"user_query":query,"route":bundle["route"],"evidence_bundle":bundle["evidence_bundle"],"response_schema":self.response_schema,"candidate_path_id":bundle["candidate_path_id"]}
        return bundle,[{"role":"system","content":self.system_prompt},{"role":"user","content":json.dumps(payload,ensure_ascii=False,indent=2)}]