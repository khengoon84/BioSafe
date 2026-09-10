
from __future__ import annotations
from pathlib import Path
import json, sys, re
from typing import Dict, Any, List

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(HERE))

from integration_authority_router_v0_1 import BioSafeIntegrationAuthorityRouterV01
from integration_safety_gate_v0_1 import classify_safety

class BioSafePipelineV01:
    def __init__(self, root:Path|str=ROOT, top_k:int=3):
        self.root=Path(root)
        self.top_k=top_k
        self.retriever=BioSafeIntegrationAuthorityRouterV01(
            self.root/"data/BioSafe_Knowledge_Base_v0.2.json",
            self.root/"data/BioSafe_Knowledge_Pack_Manifest_v0.1.json"
        )
        self.system_prompt=(self.root/"prompts/system_prompt_v0.1.txt").read_text()
        self.response_schema=json.loads((self.root/"prompts/response_schema_v0.1.json").read_text())

    def retrieve(self, query:str):
        route, evidence=self.retriever.retrieve(query,self.top_k)
        return route,evidence

    @staticmethod
    def _evidence_item(r:Dict[str,Any])->Dict[str,Any]:
        return {
            "evidence_id":r["record_id"],
            "record_type":r["record_type"],
            "document_id":r["document_id"],
            "title":r["title"],
            "authority":r["authority"],
            "jurisdiction":r["jurisdiction"],
            "section":r.get("section",""),
            "page":r.get("page",""),
            "claim_type":r.get("claim_type",""),
            "text":r.get("text",""),
            "source_url":r.get("source_url",""),
            "must_cite":r.get("must_cite",False),
            "retrieval_score":r.get("final_score")
        }

    def build_bundle(self, query:str, case_id:str|None=None, safety_class:str|None=None):
        safety=classify_safety(query)
        route,evidence=self.retrieve(query)
        if safety.restricted:
            # Safety gate is a generation-layer control. Retrieval remains frozen.
            route.domain='SAFETY'
            route.intent='refusal'
            route.jurisdiction='System'
            route.preferred_tier='System'
            route.scope=['safety','refusal','non-enabling redirect']
            route.safety_sensitive=True
            # Retrieve the system safety rule through the frozen retriever's safety route.
            route,evidence=self.retriever.retrieve(
                'unsafe biological assistance harmful enabling procedural details withhold redirect containment risk management incident prevention',
                self.top_k
            )
        return {
            "case_id":case_id,
            "user_query":query,
            "input_safety_class":safety_class,
            "route":{
                "jurisdiction":route.jurisdiction,
                "domain":route.domain,
                "intent":route.intent,
                "preferred_tier":route.preferred_tier,
                "scope":route.scope,
                "uncertainty_sensitive":route.uncertainty_sensitive,
                "safety_sensitive":route.safety_sensitive
            },
            "evidence_bundle":[self._evidence_item(r) for r in evidence],
            "response_schema":self.response_schema
        }

    def build_messages(self, query:str, case_id:str|None=None, safety_class:str|None=None):
        bundle=self.build_bundle(query,case_id,safety_class)
        user_payload={
            "task":"Answer the user query using only the supplied evidence and BioSafe policy.",
            "case_id":case_id,
            "user_query":query,
            "route":bundle["route"],
            "evidence_bundle":bundle["evidence_bundle"],
            "response_schema":self.response_schema
        }
        return bundle,[
            {"role":"system","content":self.system_prompt},
            {"role":"user","content":json.dumps(user_payload,ensure_ascii=False,indent=2)}
        ]

def load_benchmark(path:Path|str):
    cases=[]
    with open(path,encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if line: cases.append(json.loads(line))
    return cases
