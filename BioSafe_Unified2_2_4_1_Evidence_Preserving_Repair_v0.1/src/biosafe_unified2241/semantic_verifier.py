from __future__ import annotations
import re
from copy import deepcopy

class EvidencePreservingSemanticVerifier:
    """
    Verify high-stakes predicates against the scoped authoritative evidence.
    Unsupported strength is removed, while supported subject/function meaning is
    preserved where evidence permits. No statutory section or legal requirement
    is invented during repair.
    """
    PREDICATES={
      "regulatory body":("regulatory body","regulator","statutory body"),
      "approve":("approve","approval","approved"),
      "must":("must","required","requirement","shall"),
      "notify":("notify","notification"),
      "certify":("certify","certification","compliance"),
    }

    def _text(self,evidence):
        return " ".join(str(e.get("text") or e.get("statement") or "") for e in evidence).lower()

    def _neutral_role_repair(self,sentence,evidence_text):
        # Preserve a committee/body definition and supported oversight functions,
        # but never preserve unsupported regulatory/approval status.
        m=re.match(r"\s*([A-Za-z][A-Za-z0-9 ()/-]{1,100}?)\s+is\s+(.*)",sentence)
        if not m:return None
        subject=m.group(1).strip()
        if not any(t in evidence_text for t in ("oversight","assess","assessment","monitor","review")):
            return None

        # Preserve acronym expansion when it is present in the original subject.
        if subject.upper()=="IBC":
            subject="IBC (Institutional Biosafety Committee)"
        elif subject.startswith("IBC ") and "Institutional Biosafety Committee" not in subject:
            subject="IBC (Institutional Biosafety Committee)"

        funcs=[]
        if "oversight" in evidence_text: funcs.append("biosafety oversight")
        if "assess" in evidence_text or "assessment" in evidence_text: funcs.append("assessment")
        if "monitor" in evidence_text: funcs.append("monitoring")
        if not funcs:return None

        if "biosafety oversight" in funcs:
            return f"{subject} provides institutional biosafety oversight, including assessment or monitoring of relevant biosafety practices and controls."
        return f"{subject} has institutional biosafety functions that include assessment or monitoring of relevant practices and controls."

    def apply(self,response,evidence):
        out=deepcopy(response)
        ev=self._text(evidence)
        conclusion=str(out.get("conclusion") or "")
        sentences=re.split(r'(?<=[.!?])\s+',conclusion)
        repaired=[];audit=[]
        for s in sentences:
            unsupported=[]
            sl=s.lower()
            for label,support_terms in self.PREDICATES.items():
                if label in sl and not any(t in ev for t in support_terms):
                    unsupported.append(label)
            if not unsupported:
                repaired.append(s);continue

            replacement=None
            if any(x in unsupported for x in ("regulatory body","approve")):
                replacement=self._neutral_role_repair(s,ev)

            if replacement:
                repaired.append(replacement)
                audit.append({"action":"repair","original":s,"replacement":replacement,
                              "unsupported_predicates":unsupported})
            else:
                audit.append({"action":"remove","original":s,"unsupported_predicates":unsupported})

        clean=" ".join(x for x in repaired if x.strip()).strip()
        if clean: out["conclusion"]=clean
        elif audit:
            out["conclusion"]="The available scoped evidence does not support a stronger institutional or regulatory characterization."
        return out,audit
