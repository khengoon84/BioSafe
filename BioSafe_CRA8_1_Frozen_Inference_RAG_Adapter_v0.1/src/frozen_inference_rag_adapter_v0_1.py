from __future__ import annotations
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

ROOT = Path("/home/khengoon/biosafe")
for p in (ROOT, ROOT/"src", ROOT/"cra_v1"/"src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from cra_contracts_v0_1 import TaskFrame, EvidencePlan

SPECIALIZED_DOMAINS = {
    "form_e",
    "lmo_modern_biotechnology",
    "transport",
    "waste",
    "clinical_specimen",
    "biosecurity",
    "containment",
}

SOURCE_DOMAIN_HINTS = {
    "KB-MY-FORME": {"form_e"},
    "KB-MY-CU": {"lmo_modern_biotechnology"},
    "KB-MY-GMMRA": {"lmo_modern_biotechnology", "containment"},
    "KB-MY-MOH2023": {"clinical_specimen", "transport"},
    "KB-MY-DOE2005": {"waste"},
    "KB-WHO-BIOSEC": {"biosecurity"},
}

class FrozenAdapterError(RuntimeError):
    pass

@dataclass
class FrozenAdapterResult:
    response: Dict[str,Any]
    adapter_meta: Dict[str,Any]

def _workflow_name(workflow: str) -> str:
    w=(workflow or "ask").strip().lower().replace("_","-")
    if w in {"ask","review","form-e"}:
        return w
    if w in {"forme","form e"}:
        return "form-e"
    raise FrozenAdapterError(f"unsupported workflow: {workflow}")

def _source_id(item: Any) -> Optional[str]:
    if isinstance(item,str):
        return item
    if isinstance(item,dict):
        for key in ("source_id","document_id","authority_id","id","source"):
            val=item.get(key)
            if isinstance(val,str) and val:
                return val
    return None

def _infer_output_domains(response: Dict[str,Any]) -> set[str]:
    domains=set()
    for container_key in ("applicable_authority","evidence"):
        values=response.get(container_key) or []
        if not isinstance(values,list):
            continue
        for item in values:
            sid=_source_id(item)
            if not sid:
                continue
            for hint,ds in SOURCE_DOMAIN_HINTS.items():
                if sid.startswith(hint) or hint in sid:
                    domains.update(ds)
    return domains

def validate_frozen_response_against_plan(
    response: Dict[str,Any],
    frame: TaskFrame,
    plan: EvidencePlan,
) -> Dict[str,Any]:
    if not isinstance(response,dict):
        raise FrozenAdapterError("frozen inference service returned non-dict response")

    required_fields={
        "conclusion","applicable_authority","evidence","missing_information",
        "recommended_next_step","limitations","safety"
    }
    missing=sorted(required_fields-set(response.keys()))
    if missing:
        raise FrozenAdapterError("frozen response missing required fields: "+", ".join(missing))

    active=set(frame.activated_domains)
    excluded=set(plan.exclude_domains)
    inferred=_infer_output_domains(response)
    leaked=(inferred & excluded & SPECIALIZED_DOMAINS)

    if leaked:
        raise FrozenAdapterError(
            "domain leakage from frozen inference response: "+", ".join(sorted(leaked))
        )

    if plan.skip_rag:
        raise FrozenAdapterError("skip_rag task must not call frozen inference adapter")

    return {
        "active_domains": sorted(active),
        "excluded_domains": sorted(excluded),
        "output_domains_detected": sorted(inferred),
        "domain_leakage": [],
    }

class FrozenInferenceRAGAdapterV01:
    """
    Adapter around the validated Stage 8/9 inference service.

    It does not edit or subclass the frozen service. The service is injected
    for tests and imported lazily for live use.
    """
    def __init__(
        self,
        project_root: str|Path = ROOT,
        service_factory: Optional[Callable[[],Any]] = None,
    ):
        self.root=Path(project_root)
        self._service_factory=service_factory
        self._service=None

    def _get_service(self):
        if self._service is not None:
            return self._service
        if self._service_factory is not None:
            self._service=self._service_factory()
            return self._service

        from full_inference_service_v0_1 import BioSafeFullInferenceServiceV011
        self._service=BioSafeFullInferenceServiceV011(project_root=self.root)
        return self._service

    def run(
        self,
        frame: TaskFrame,
        plan: EvidencePlan,
        retrieval_request: Dict[str,Any],
        *,
        documents: Optional[List[Dict[str,Any]]] = None,
        workflow: str = "ask",
    ) -> FrozenAdapterResult:
        if plan.skip_rag or retrieval_request.get("skip",False):
            raise FrozenAdapterError("CRA plan requires RAG bypass; frozen service was not called")

        rr_domains=set(retrieval_request.get("required_domains") or [])
        frame_domains=set(frame.activated_domains)
        if rr_domains != frame_domains:
            raise FrozenAdapterError(
                f"retrieval/frame domain mismatch: retrieval={sorted(rr_domains)} frame={sorted(frame_domains)}"
            )

        wf=_workflow_name(workflow)
        service=self._get_service()

        response=service.infer(
            frame.current_question,
            documents=list(documents or []),
            workflow=wf,
        )

        meta=validate_frozen_response_against_plan(response,frame,plan)
        meta.update({
            "adapter_version":"CRA-8.1-v0.1",
            "workflow":wf,
            "frozen_service":"BioSafeFullInferenceServiceV011",
            "query_rewritten":False,
            "documents_forwarded":len(documents or []),
        })
        return FrozenAdapterResult(response=response,adapter_meta=meta)

def make_domain_callback(
    adapter: FrozenInferenceRAGAdapterV01,
    *,
    documents: Optional[List[Dict[str,Any]]] = None,
    workflow: str = "ask",
):
    def callback(frame: TaskFrame, plan: EvidencePlan, retrieval_request: Dict[str,Any]):
        result=adapter.run(
            frame,plan,retrieval_request,
            documents=documents,
            workflow=workflow,
        )
        out=dict(result.response)
        out["_cra_adapter"]=result.adapter_meta
        return out
    return callback
