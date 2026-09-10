import io, sys
from pathlib import Path
ROOT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(ROOT/"cra_v1"/"src"))

from frozen_inference_rag_adapter_v0_1 import FrozenAdapterResult
from cra_service_runtime_v0_1 import CRAServiceRuntimeV01
from cra_bridge_app_v0_1 import create_app

checks=[]
def check(name,cond):
    print(("PASS" if cond else "FAIL"),name); checks.append(bool(cond))

class FakeAdapter:
    def __init__(self): self.calls=[]
    def run(self,frame,plan,retrieval_request,documents=None,workflow="ask"):
        self.calls.append((frame,plan,retrieval_request,documents or [],workflow))
        return FrozenAdapterResult(
            response={
                "conclusion":f"fake-{workflow}",
                "applicable_authority":[],
                "evidence":[],
                "missing_information":[],
                "recommended_next_step":[],
                "limitations":["Advisory only."],
                "safety":{"classification":"normal","response_mode":"answer","reason":""}
            },
            adapter_meta={"workflow":workflow,"domain_leakage":[]}
        )

fake=FakeAdapter()
client=create_app(CRAServiceRuntimeV01(adapter=fake)).test_client()

r=client.get("/health"); j=r.get_json()
check("health 200",r.status_code==200)
check("sidecar 8766",j["port"]==8766)
check("UI untouched",j["live_ui_modified"] is False)

r=client.post("/api/ask",json={"query":"who are you?"}); j=r.get_json()
check("ask product help 200",r.status_code==200 and j["route"]=="product_help_bypass")
sid=j["session_id"]

r=client.post("/api/ask",json={"query":"What is the biosafety requirement for this work?","session_id":sid}); j=r.get_json()
check("ask domain 200",r.status_code==200 and j["route"]=="frozen_domain_adapter")
check("same session",j["session_id"]==sid)

data={"query":"Please assess the biosafety gaps.","file":(io.BytesIO(b"Example SOP content"),"sample_sop.txt")}
r=client.post("/api/review",data=data,content_type="multipart/form-data"); j=r.get_json()
check("review 200",r.status_code==200)
check("review structured metadata",j["_document"]["filename"]=="sample_sop.txt")
check("review domain","document_review" in j["task_frame"]["activated_domains"])

r=client.post("/api/form-e",json={"query":"I am culturing a modified strain."}); j=r.get_json()
check("Form E 200",r.status_code==200)
check("Form E domain","form_e" in j["task_frame"]["activated_domains"])

check("blank ask 400",client.post("/api/ask",json={}).status_code==400)
check("blank Form E 400",client.post("/api/form-e",json={}).status_code==400)
check("review requires file",client.post("/api/review",data={"query":"Review"}).status_code==400)

r=client.post("/api/session/reset",json={"session_id":sid}); j=r.get_json()
check("reset 200",r.status_code==200 and j["reset"] is True)

print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-8.2 Flask HTTP contract v0.1: PASS")
