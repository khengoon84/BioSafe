from copy import deepcopy
class ResponseTypeContractEnforcer:
    def apply(self,response,intent):
        out=deepcopy(response); audit=[]
        if intent in {"simple_answer","product_help","self_knowledge","educational_answer"}:
            for k in ("missing_information","recommended_next_step"):
                if out.get(k): out[k]=[]; audit.append("cleared_"+k)
        if intent=="educational_answer":
            old=out.get("limitations",[]) or []
            out["limitations"]=[x for x in old if not any(t in str(x).lower()
                for t in ("document review","certify regulatory compliance","regulatory approval"))]
            if out["limitations"]!=old:audit.append("cleared_educational_boilerplate")
            s=out.get("safety")
            if isinstance(s,dict) and s.get("classification")=="caution":
                reason=str(s.get("reason") or "").lower()
                if not reason or "document review" in reason or "compliance" in reason:
                    out["safety"]={"classification":"normal","response_mode":"answer","reason":""}
                    audit.append("normalized_educational_safety")
        return out,audit
