import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))

from frozen_inference_rag_adapter_v0_1 import FrozenAdapterResult
from cra_service_runtime_v0_1 import CRAServiceRuntimeV01

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

class FakeAdapter:
    def __init__(self):
        self.calls=[]
    def run(self,frame,plan,retrieval_request,documents=None,workflow="ask"):
        self.calls.append({
            "frame":frame,"plan":plan,"retrieval":retrieval_request,
            "documents":documents or [],"workflow":workflow
        })
        source={"form-e":"KB-MY-FORME","review":"KB-WHO-LBM4","ask":"KB-WHO-RA"}[workflow]
        return FrozenAdapterResult(
            response={
                "conclusion":f"fake-{workflow}-response",
                "applicable_authority":[source],
                "evidence":[{"source_id":source,"statement":"evidence"}],
                "missing_information":[],
                "recommended_next_step":[],
                "limitations":["Advisory only."],
                "safety":{"classification":"normal","response_mode":"answer","reason":""}
            },
            adapter_meta={"workflow":workflow,"domain_leakage":[]}
        )

fake=FakeAdapter()
rt=CRAServiceRuntimeV01(adapter=fake)

x=rt.handle("who are you?")
check("identity bypass",x["route"]=="product_help_bypass")
check("identity no frozen call",len(fake.calls)==0)
sid=x["session_id"]

x=rt.handle("what can you do?",session_id=sid)
check("session continuity",x["session_id"]==sid)
check("turn increment",x["turn_id"].endswith("-t2"))

x=rt.handle("What is the biosafety requirement for this work?",session_id=sid)
check("general biosafety adapter",x["route"]=="frozen_domain_adapter")
check("general biosafety only",x["task_frame"]["activated_domains"]==["general_biosafety"])
check("Form E excluded","form_e" in x["_cra_bridge"]["excluded_domains"])
check("ask workflow forwarded",fake.calls[-1]["workflow"]=="ask")

x=rt.handle("What are the transport requirements for this specimen?")
check("transport active",x["task_frame"]["activated_domains"]==["transport"])
check("transport retrieval",x["_cra_bridge"]["required_domains"]==["transport"])

docs=[{"filename":"sample_sop.txt","text":"Example SOP content"}]
x=rt.handle("Please assess the biosafety gaps.",workflow="review",documents=docs)
check("review domain forced","document_review" in x["task_frame"]["activated_domains"])
check("review workflow forwarded",fake.calls[-1]["workflow"]=="review")
check("review document structured",fake.calls[-1]["documents"]==docs)
check("review query clean","USER DOCUMENT" not in fake.calls[-1]["frame"].current_question)

x=rt.handle("I am culturing a modified strain in the laboratory.",workflow="form-e")
check("Form E domain forced","form_e" in x["task_frame"]["activated_domains"])
check("Form E workflow forwarded",fake.calls[-1]["workflow"]=="form-e")

try:
    rt.handle("")
    check("blank query rejected",False)
except ValueError:
    check("blank query rejected",True)

try:
    rt.handle("x",workflow="admin")
    check("bad workflow rejected",False)
except ValueError:
    check("bad workflow rejected",True)

check("reset existing session",rt.sessions.reset(sid) is True)
x=rt.handle("who are you?",session_id=sid)
check("reset restarts turn",x["turn_id"].endswith("-t1"))

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-8.2 service runtime v0.1: PASS")
