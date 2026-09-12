from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


class EvidenceAwareSubjectCoverageGuard:
    """C5-only coverage wrapper; the frozen guard remains the fallback."""

    FACETS=(
        ("purpose", re.compile(r"^\s*what is the purpose of (.+?)[?.!]*\s*$", re.I)),
        ("definition", re.compile(r"^\s*(?:what is|define|meaning of) (.+?)[?.!]*\s*$", re.I)),
        ("role", re.compile(r"^\s*what role does (.+?) (?:have|play)[?.!]*\s*$", re.I)),
        ("scope", re.compile(r"^\s*what does (.+?) cover[?.!]*\s*$", re.I)),
    )
    PURPOSE_TYPES={"purpose","objective","function","risk_assessment_purpose"}
    DEFINITION_TYPES={"definition","hazard_definition","risk_definition"}
    ROLE_TYPES={"role","function","oversight","responsibility"}
    SCOPE_TYPES={"scope","risk_assessment_scope"}

    def __init__(self, fallback: Any):
        self.fallback=fallback
        self.current_plan: dict[str, Any] = {}

    def set_plan(self, plan: dict[str, Any]) -> None:
        self.current_plan=dict(plan or {})

    @classmethod
    def facet(cls, query: str) -> tuple[str, str] | None:
        for name, pattern in cls.FACETS:
            match=pattern.match(query or "")
            if match:
                subject=match.group(1).strip(" ?.! ")
                if any(x in subject.lower() for x in ("my project", "my activity", "this project", "start work", "sufficient")):
                    return None
                return name,subject
        return None

    @classmethod
    def _supported(cls, facet: str, subject: str, evidence: list[dict[str, Any]]) -> list[str]:
        type_map={"purpose":cls.PURPOSE_TYPES,"definition":cls.DEFINITION_TYPES,"role":cls.ROLE_TYPES,"scope":cls.SCOPE_TYPES}
        allowed=type_map.get(facet,set()); subject_terms={x for x in re.findall(r"[a-z0-9]+",subject.lower()) if len(x)>3}
        found=[]
        for item in evidence or []:
            if item.get("evidence_origin") != "C5_REVIEWED_CANDIDATE" or item.get("candidate_path_id") != "C37_METADATA_CFG02:metadata_off":
                continue
            if not item.get("verification_status") or not item.get("source_sha256") or not item.get("support_spans"):
                continue
            claim_type=str(item.get("claim_type") or "").lower()
            text=str(item.get("text") or item.get("statement") or "").lower()
            if claim_type in allowed or len(subject_terms & set(re.findall(r"[a-z0-9]+",text))) >= max(1,min(2,len(subject_terms))):
                found.append(str(item.get("evidence_id")))
        return found

    def apply(self, response: dict[str, Any], query: str, evidence: list[dict[str, Any]], evidence_plan: dict[str, Any] | None = None):
        out=deepcopy(response)
        parsed=self.facet(query)
        plan=evidence_plan or self.current_plan or {"retrieval_required": bool(parsed)}
        if parsed and plan.get("retrieval_required"):
            facet,subject=parsed; supporting=self._supported(facet,subject,evidence)
            if supporting:
                return out,[{"action":"coverage_satisfied_by_structured_evidence","facet":facet,"subject":subject,"supporting_evidence_ids":supporting,"candidate_path_id":"C37_METADATA_CFG02:metadata_off"}]
        return self.fallback.apply(out,query,evidence)