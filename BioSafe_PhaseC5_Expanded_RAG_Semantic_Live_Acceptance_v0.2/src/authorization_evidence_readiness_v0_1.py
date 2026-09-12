from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from authorization_verifier_v0_2 import load_ontology

HERE=Path(__file__).resolve().parent
REPORT_PATH=HERE.parent/"reports/authorization_evidence_readiness_v0_1.json"


def _is_authorization_type(claim_type: str, ontology: dict[str, Any]) -> bool:
    known={claim_type_name for spec in ontology["authorization_concepts"].values()
           for claim_type_name in spec.get("positive_support_claim_types",[])+spec.get("negative_support_claim_types",[])}
    return claim_type.lower() in {item.lower() for item in known}


def evaluate_evidence_readiness(claims: list[dict[str, Any]], ontology: dict[str, Any] | None=None) -> dict[str, Any]:
    ontology=ontology or load_ontology()
    required=tuple(ontology["required_evidence_fields"])
    authorization=[item for item in claims if _is_authorization_type(str(item.get("claim_type") or ""),ontology)]
    missing_by_field={field:0 for field in required}
    metadata_complete=[]
    positive=negative=0
    for item in authorization:
        for field in required:
            if not str(item.get(field) or "").strip():
                missing_by_field[field]+=1
        if all(str(item.get(field) or "").strip() for field in required):
            metadata_complete.append(item)
        polarity=str(item.get("polarity") or "").upper()
        if polarity=="REQUIRED": positive+=1
        if polarity in {"NOT_REQUIRED","EXEMPT"}: negative+=1
    return {
        "artifact_version":"BioSafe_C5_Authorization_Evidence_Readiness_v0.1",
        "authorization_claim_count":len(authorization),
        "authorization_claim_types":sorted({str(item.get("claim_type") or "") for item in authorization}),
        "metadata_complete_count":len(metadata_complete),
        "missing_required_metadata":missing_by_field,
        "positive_support_count":positive,
        "negative_support_count":negative,
        "positive_claims_renderable":False,
        "negative_claims_renderable":False,
        "result":("READY_FOR_REVIEWED_AUTHORIZATION_CLAIMS" if metadata_complete else "NO_REVIEWED_AUTHORIZATION_CLAIMS"),
        "claim_use_status":"REVIEW_REQUIRED_BEFORE_CLAIM_USE",
        "live_activation_status":"PROHIBITED_PENDING_PHASE_C_GATES",
    }


def write_readiness_report(claims: list[dict[str, Any]], path: Path=REPORT_PATH) -> dict[str, Any]:
    report=evaluate_evidence_readiness(claims)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return report


if __name__=="__main__":
    root=HERE.parents[1]
    kb=json.loads((root/"data/BioSafe_Knowledge_Base_v0.2.json").read_text(encoding="utf-8"))
    print(json.dumps(write_readiness_report(kb.get("claims",[])),indent=2))