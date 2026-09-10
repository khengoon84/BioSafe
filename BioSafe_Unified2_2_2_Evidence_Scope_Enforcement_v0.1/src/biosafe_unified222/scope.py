
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Dict,List

REGULATORY_HINTS=(
    "act","regulation","regulations","notification","notify","approval","compliance",
    "director general","form e","legal","law","statutory","requirement","required"
)
FORM_E_HINTS=("form e","assessment report","annex")
IBC_HINTS=("institutional biosafety committee","ibc")
FOUNDATIONAL_HINTS=("who","laboratory biosafety manual","biosecurity guidance","biosafety","biosecurity")

@dataclass
class ScopeResult:
    evidence:list
    removed:list
    mode:str

class EvidenceScopeEnforcer:
    """
    Post-retrieval, pre-generation evidence filter.
    It does not modify retrieval/ranking. It removes evidence families that the
    Evidence Requirement Planner did not activate.
    """
    def _blob(self,e:Dict[str,Any])->str:
        return " ".join(str(e.get(k,"")) for k in
            ("document_id","title","authority","jurisdiction","section","claim_type","text")).lower()

    def apply(self,evidence:List[Dict[str,Any]],plan:Dict[str,Any],query:str)->ScopeResult:
        mode=(plan or {}).get("retrieval_mode","none")
        q=(query or "").lower()
        keep=[]; removed=[]
        for e in evidence or []:
            b=self._blob(e)
            regulatory=any(x in b for x in REGULATORY_HINTS) or "department of biosafety" in b
            forme=any(x in b for x in FORM_E_HINTS)
            ibc=any(x in b for x in IBC_HINTS)
            foundational=("world health organization" in b or "kb-who-" in b)

            allowed=True
            if mode in ("none","context_only"):
                allowed=False
            elif mode=="general_guidance":
                # Foundational educational questions should not inherit Malaysian
                # regulatory/Form-E/IBC decision evidence merely because it ranked.
                allowed=foundational and not forme
            elif mode=="regulatory":
                allowed=True
            elif mode=="document_plus_authority":
                allowed=True
            elif mode=="form_e_regulatory":
                allowed=True
            elif mode=="safe_guidance_only":
                allowed=foundational and not regulatory

            (keep if allowed else removed).append(e)
        return ScopeResult(keep,removed,mode)
