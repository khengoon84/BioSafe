import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))

from cra_contracts_v0_1 import *
from frozen_inference_rag_adapter_v0_1 import *

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

def mk_frame(domains,question="What are the transport requirements?"):
    return TaskFrame(
        task_id="t",
        interaction_type=InteractionType.NEW_TASK,
        user_goal="answer",
        current_question=question,
        jurisdiction="Malaysia",
        activated_domains=list(domains),
        inactive_domains=[]
    )

def mk_plan(domains,exclude=None,skip=False):
    return EvidencePlan(
        skip_rag=skip,
        required_domains=list(domains),
        required_evidence_types=["guidance"] if not skip else [],
        preferred_authority_tiers=[1,2] if not skip else [],
        exclude_domains=list(exclude or []),
        jurisdiction="Malaysia"
    )

class FakeService:
    def __init__(self,response):
        self.response=response
        self.calls=[]
    def infer(self,query,documents=None,workflow="ask"):
        self.calls.append({"query":query,"documents":documents or [],"workflow":workflow})
        return dict(self.response)

def good_response(source="KB-MY-MOH2023"):
    return {
        "conclusion":"Assessment.",
        "applicable_authority":[source] if source else [],
        "evidence":[{"source_id":source,"statement":"Supported evidence."}] if source else [],
        "missing_information":[],
        "recommended_next_step":[],
        "limitations":["Advisory only."],
        "safety":{"classification":"normal","response_mode":"answer","reason":""},
        "_meta":{"model_called":True}
    }

fake=FakeService(good_response())
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
f=mk_frame(["transport"])
p=mk_plan(["transport"],["form_e","waste"])
r=a.run(f,p,{"skip":False,"required_domains":["transport"]},workflow="ask")
check("frozen service called once",len(fake.calls)==1)
check("original query preserved",fake.calls[0]["query"]==f.current_question)
check("ask workflow preserved",fake.calls[0]["workflow"]=="ask")
check("query not rewritten",r.adapter_meta["query_rewritten"] is False)

fake=FakeService(good_response("KB-WHO-LBM4"))
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
docs=[{"filename":"sample_sop.txt","text":"SOP text"}]
f=mk_frame(["document_review"],"Review this document.")
p=mk_plan(["document_review"],["form_e"])
r=a.run(f,p,{"skip":False,"required_domains":["document_review"]},documents=docs,workflow="review")
check("review workflow forwarded",fake.calls[0]["workflow"]=="review")
check("documents forwarded",fake.calls[0]["documents"]==docs)
check("document count meta",r.adapter_meta["documents_forwarded"]==1)

fake=FakeService(good_response("KB-MY-FORME"))
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
f=mk_frame(["form_e"],"Do I need Form E?")
p=mk_plan(["form_e"],["transport","waste"])
r=a.run(f,p,{"skip":False,"required_domains":["form_e"]},workflow="forme")
check("Form E workflow normalized",fake.calls[0]["workflow"]=="form-e")
check("Form E allowed when active","form_e" in r.adapter_meta["output_domains_detected"])

fake=FakeService(good_response())
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
f=mk_frame([])
p=mk_plan([],skip=True)
try:
    a.run(f,p,{"skip":True,"required_domains":[]})
    check("skip-rag blocked",False)
except FrozenAdapterError:
    check("skip-rag blocked",True)
check("skip-rag service not called",len(fake.calls)==0)

fake=FakeService(good_response())
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
try:
    a.run(mk_frame(["transport"]),mk_plan(["transport"]),{"skip":False,"required_domains":["waste"]})
    check("domain mismatch blocked",False)
except FrozenAdapterError:
    check("domain mismatch blocked",True)
check("mismatch service not called",len(fake.calls)==0)

fake=FakeService(good_response("KB-MY-FORME"))
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
try:
    a.run(mk_frame(["general_biosafety"]),mk_plan(["general_biosafety"],["form_e","transport","waste"]),
          {"skip":False,"required_domains":["general_biosafety"]})
    check("Form E leakage blocked",False)
except FrozenAdapterError:
    check("Form E leakage blocked",True)

fake=FakeService(good_response("KB-MY-MOH2023"))
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
r=a.run(mk_frame(["transport"]),mk_plan(["transport"],["form_e","waste"]),
        {"skip":False,"required_domains":["transport"]})
check("transport source allowed","transport" in r.adapter_meta["output_domains_detected"])
check("no leakage recorded",r.adapter_meta["domain_leakage"]==[])

fake=FakeService(good_response("KB-MY-DOE2005"))
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
try:
    a.run(mk_frame(["transport"]),mk_plan(["transport"],["form_e","waste"]),
          {"skip":False,"required_domains":["transport"]})
    check("waste leakage blocked",False)
except FrozenAdapterError:
    check("waste leakage blocked",True)

bad={"conclusion":"x"}
fake=FakeService(bad)
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
try:
    a.run(mk_frame(["transport"]),mk_plan(["transport"]),{"skip":False,"required_domains":["transport"]})
    check("response schema enforced",False)
except FrozenAdapterError:
    check("response schema enforced",True)

fake=FakeService(good_response())
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
try:
    a.run(mk_frame(["transport"]),mk_plan(["transport"]),{"skip":False,"required_domains":["transport"]},workflow="admin")
    check("unsupported workflow blocked",False)
except FrozenAdapterError:
    check("unsupported workflow blocked",True)
check("unsupported workflow service not called",len(fake.calls)==0)

fake=FakeService(good_response("KB-MY-MOH2023"))
a=FrozenInferenceRAGAdapterV01(service_factory=lambda:fake)
cb=make_domain_callback(a,workflow="ask")
out=cb(mk_frame(["transport"]),mk_plan(["transport"],["form_e","waste"]),
       {"skip":False,"required_domains":["transport"]})
check("callback preserves conclusion",out["conclusion"]=="Assessment.")
check("callback adds CRA namespace","_cra_adapter" in out)
check("frozen meta preserved","_meta" in out)

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-8.1 Frozen Inference/RAG Adapter v0.1: PASS")
