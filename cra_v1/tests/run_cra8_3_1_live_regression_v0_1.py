from __future__ import annotations
import json, urllib.request, uuid
from pathlib import Path
from datetime import datetime, timezone

BASE="http://127.0.0.1:8767"
ROOT=Path("/home/khengoon/biosafe")
REPORT=ROOT/"cra_v1"/"reports"/"cra8_3_1_regression_report_v0_1.json"
FIXTURE=ROOT/"cra_v1"/"fixtures"/"sample_review_sop.txt"

results=[]
def post(path,payload,timeout=900):
    req=urllib.request.Request(BASE+path,data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.status,json.loads(r.read().decode())

def post_multipart(path,fields,file_name,file_bytes,timeout=900):
    b="----BioSafe"+uuid.uuid4().hex
    parts=[]
    for k,v in fields.items():
        parts += [f"--{b}\r\n".encode(),f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode(),str(v).encode(),b"\r\n"]
    parts += [f"--{b}\r\n".encode(),f'Content-Disposition: form-data; name="file"; filename="{file_name}"\r\n'.encode(),
              b"Content-Type: text/plain\r\n\r\n",file_bytes,b"\r\n",f"--{b}--\r\n".encode()]
    req=urllib.request.Request(BASE+path,data=b"".join(parts),method="POST",
        headers={"Content-Type":f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.status,json.loads(r.read().decode())

def rec(cid,name,checks,detail):
    bad=[k for k,v in checks.items() if not v]
    row={"case_id":cid,"name":name,"passed":not bad,"assertions":checks,"failures":bad,"details":detail}
    results.append(row)
    print(("PASS" if not bad else "FAIL"),cid,name,f"({sum(checks.values())}/{len(checks)})")
    if bad: print("  failures:",", ".join(bad))

# F01 follow-up continuity
_,first=post("/api/ask",{"query":"What are the transport requirements for this specimen?"})
sid=first["session_id"]
_,follow=post("/api/ask",{"query":"Why does that matter?","session_id":sid})
rec("F01","referential_followup_continuity",{
    "same_session":follow["session_id"]==sid,
    "classified_followup":follow["interaction_type"]=="FOLLOW_UP",
    "continuity_repaired":follow["_cra_bridge"]["continuity_repaired"] is True,
    "transport_inherited":"transport" in follow["task_frame"]["activated_domains"],
    "reference_or_domain_preserved":bool(follow["_cra_bridge"]["resolved_reference"]) or "transport" in follow["_cra_bridge"]["inherited_domains"],
    "not_placeholder":follow["response"].get("direct_answer")!="I can continue from the previous context, but this turn does not require a new regulatory retrieval.",
},follow)

# F02 document review domain leakage
_,review=post_multipart("/api/review",
    {"query":"Review this SOP for biosafety gaps and missing information."},
    "sample_review_sop.txt",FIXTURE.read_bytes())
r=review["response"]
blob=" ".join([
    str(r.get("conclusion","")),
    " ".join(map(str,r.get("missing_information") or [])),
    " ".join(map(str,r.get("recommended_next_step") or [])),
]).lower()
rec("F02","review_output_domain_enforcement",{
    "document_review_active":"document_review" in review["task_frame"]["activated_domains"],
    "form_e_inactive":"form_e" not in review["task_frame"]["activated_domains"],
    "lmo_inactive":"lmo_modern_biotechnology" not in review["task_frame"]["activated_domains"],
    "no_form_e_output":"form e" not in blob,
    "no_lmo_output":"lmo" not in blob,
    "quality_guard_ran":"_cra_quality" in r,
},review)

# F03 recommendation grounding
_,forme=post("/api/form-e",{
    "query":"I am culturing a genetically modified bacterial strain in a contained research laboratory. Help me identify what information is still needed for the researcher-facing Form E workflow."
})
steps=" ".join(map(str,forme["response"].get("recommended_next_step") or [])).lower()
rec("F03","form_e_recommendation_grounding",{
    "form_e_active":"form_e" in forme["task_frame"]["activated_domains"],
    "no_unsupported_lab_director":"laboratory director" not in steps,
    "no_unsupported_clearance":"biosafety clearance" not in steps,
    "quality_guard_ran":"_cra_quality" in forme["response"],
},forme)

summary={
    "benchmark":"BioSafe CRA-8.3.1 Integration Quality Correction v0.1",
    "generated_at_utc":datetime.now(timezone.utc).isoformat(),
    "cases_total":len(results),
    "cases_passed":sum(r["passed"] for r in results),
    "assertions_total":sum(len(r["assertions"]) for r in results),
    "assertions_passed":sum(sum(r["assertions"].values()) for r in results),
    "results":results,
}
REPORT.parent.mkdir(parents=True,exist_ok=True)
REPORT.write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding="utf-8")
print()
print(f'Case summary: {summary["cases_passed"]}/{summary["cases_total"]} passed')
print(f'Assertion summary: {summary["assertions_passed"]}/{summary["assertions_total"]} passed')
print("Report:",REPORT)
if summary["cases_passed"]!=summary["cases_total"]:
    raise SystemExit(1)
print("CRA-8.3.1 live correction regression: PASS")
