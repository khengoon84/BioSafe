from typing import Dict, Any
from cra_contracts_v0_1 import EvidencePlan, TaskFrame

DOMAIN_QUERY_HINTS = {
    "general_biosafety": "biosafety risk assessment laboratory safety",
    "containment": "containment biosafety level risk assessment",
    "lmo_modern_biotechnology": "LMO modern biotechnology applicability notification",
    "form_e": "Form E contained use LMO notification researcher",
    "transport": "clinical specimen infectious substance transport packaging",
    "waste": "biological waste scheduled waste disposal",
    "clinical_specimen": "clinical specimen handling biosafety",
    "biosecurity": "laboratory biosecurity guidance",
    "document_review": "biosafety risk assessment review criteria",
}

def build_retrieval_request(frame: TaskFrame, plan: EvidencePlan) -> Dict[str,Any]:
    if plan.skip_rag:
        return {
            "skip": True,
            "query": None,
            "required_domains": [],
            "exclude_domains": list(plan.exclude_domains),
            "jurisdiction": plan.jurisdiction,
        }

    hints=[DOMAIN_QUERY_HINTS[d] for d in plan.required_domains if d in DOMAIN_QUERY_HINTS]
    query=" | ".join(hints)
    return {
        "skip": False,
        "query": query,
        "required_domains": list(plan.required_domains),
        "required_evidence_types": list(plan.required_evidence_types),
        "exclude_domains": list(plan.exclude_domains),
        "jurisdiction": plan.jurisdiction,
        "task_id": frame.task_id,
    }
