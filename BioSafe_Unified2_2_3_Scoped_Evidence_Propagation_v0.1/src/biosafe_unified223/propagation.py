import copy,json
class ScopedPipelineAdapter:
    """Scope the bundle immediately after frozen retrieval, before all downstream consumers."""
    def __init__(self,pipeline,enforcer,plan,query):
        self.pipeline,self.enforcer,self.plan,self.query=pipeline,enforcer,plan,query
        self.audit={"kept_ids":[],"removed_ids":[]}
    def build_messages(self,*args,**kwargs):
        result=self.pipeline.build_messages(*args,**kwargs)
        items=list(result)
        bi=next(i for i,x in enumerate(items) if isinstance(x,dict) and "evidence_bundle" in x)
        mi=next((i for i,x in enumerate(items) if isinstance(x,list) and x and isinstance(x[0],dict) and "role" in x[0]),None)
        b=copy.deepcopy(items[bi])
        sr=self.enforcer.apply(b.get("evidence_bundle",[]),self.plan.__dict__,self.query)
        b["evidence_bundle"]=sr.evidence
        self.audit={"kept_ids":[e.get("evidence_id") for e in sr.evidence],
                    "removed_ids":[e.get("evidence_id") for e in sr.removed]}
        items[bi]=b
        if mi is not None and len(items[mi])>=2:
            m=copy.deepcopy(items[mi])
            try:
                p=json.loads(m[1]["content"]);p["evidence_bundle"]=b["evidence_bundle"]
                m[1]["content"]=json.dumps(p,ensure_ascii=False,indent=2)
            except Exception: pass
            items[mi]=m
        return tuple(items) if isinstance(result,tuple) else items
