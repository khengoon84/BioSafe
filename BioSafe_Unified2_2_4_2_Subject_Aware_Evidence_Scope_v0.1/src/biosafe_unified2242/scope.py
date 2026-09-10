from __future__ import annotations
import re
from copy import deepcopy
from biosafe_unified222 import EvidenceScopeEnforcer

class SubjectAwareEvidenceScopeEnforcer:
    """
    Wrap the validated EvidenceScopeEnforcer.

    General invariant:
    If the user explicitly asks about a named institutional/governance subject,
    a narrow authoritative source that directly defines or describes that subject
    may be restored into an otherwise general-guidance scope.

    This is NOT jurisdiction activation. It does not reopen broad Malaysian law,
    Form E, or unrelated regulatory material.
    """
    def __init__(self):
        self.base=EvidenceScopeEnforcer()

    @staticmethod
    def _acronyms(query):
        # Explicit acronyms such as PI, IBC, BSC. Common English words are excluded.
        stop={"WHAT","IS","AND","THE","WHO","HOW","DO","I","MY"}
        return {x for x in re.findall(r'\b[A-Z][A-Z0-9-]{1,7}\b',query) if x not in stop}

    @staticmethod
    def _whole(text,token):
        return re.search(r'(?<![A-Za-z0-9])'+re.escape(token)+r'(?![A-Za-z0-9])',text,re.I) is not None

    @staticmethod
    def _is_narrow_subject_evidence(item,subjects,query):
        text=" ".join(str(item.get(k) or "") for k in
                      ("title","text","section","document_id","claim_type"))
        if not any(SubjectAwareEvidenceScopeEnforcer._whole(text,s) for s in subjects):
            return False

        q=query.lower()
        tl=text.lower()

        # Application/report-specific material is not restored unless explicitly requested.
        excluded=("form e","assessment report","application form","submission form")
        if any(x in tl for x in excluded) and not any(x in q for x in excluded):
            return False

        # Prefer definition/function/role evidence rather than broad legal consequences.
        role_terms=("function","role","responsib","oversight","committee","principal investigator",
                    "assessment","monitoring","means","defined","definition","accountable")
        return any(x in tl for x in role_terms)

    def apply(self,evidence,plan,query):
        result=self.base.apply(evidence,plan,query)
        mode=getattr(result,"mode",None) or (plan.get("mode") if isinstance(plan,dict) else None)
        subjects=self._acronyms(query)

        # Only narrow educational/general-guidance restoration.
        if mode not in {"general_guidance","international_or_foundational"} or not subjects:
            return result

        kept=list(result.evidence)
        kept_ids={x.get("evidence_id") for x in kept}
        restored=[]
        still_removed=[]
        for item in result.removed:
            if len(restored)<2 and item.get("evidence_id") not in kept_ids and \
               self._is_narrow_subject_evidence(item,subjects,query):
                restored.append(deepcopy(item))
            else:
                still_removed.append(item)

        result.evidence=kept+restored
        result.removed=still_removed
        # Optional audit fields are attached dynamically; existing callers remain compatible.
        result.subject_activation={
            "subjects":sorted(subjects),
            "restored_ids":[x.get("evidence_id") for x in restored],
        }
        return result
