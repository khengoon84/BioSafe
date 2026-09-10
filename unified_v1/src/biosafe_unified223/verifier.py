import re
class SemanticClaimVerifier:
    """Conservative support check for high-stakes predicates in model-authored conclusions."""
    RULES=[
      ("regulatory body",("regulatory body","regulator","statutory body")),
      ("approve",("approve","approval","approved")),
      ("must",("must","required","requirement","shall")),
      ("notify",("notify","notification")),
      ("certify",("certify","certification","compliance"))]
    def apply(self,response,evidence):
        out=dict(response); ev=" ".join(str(e.get("text","")) for e in evidence).lower()
        sentences=re.split(r'(?<=[.!?])\s+',str(out.get("conclusion") or ""))
        kept=[];unsupported=[]
        for s in sentences:
            bad=[label for label,terms in self.RULES if label in s.lower() and not any(t in ev for t in terms)]
            if bad: unsupported.append({"sentence":s,"unsupported_predicates":bad})
            else: kept.append(s)
        if unsupported:
            out["conclusion"]=" ".join(x for x in kept if x.strip()).strip() or \
              "The available scoped evidence does not support a stronger institutional or regulatory characterization."
        return out,unsupported
