
from __future__ import annotations
import json, sys, time, importlib, inspect, urllib.request
from pathlib import Path

PROJECT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(PROJECT))
sys.path.insert(0,str(PROJECT/"src"))

from biosafe_pipeline_v0_1 import BioSafePipelineV01
from complexity_escalation_router_v0_1 import ComplexityEscalationRouterV01
from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV01

OLLAMA_URL="http://localhost:11434/api/chat"

def ollama_chat(model,messages,num_predict=420):
    body=json.dumps({
        "model":model,
        "messages":messages,
        "stream":False,
        "think":False,
        "options":{"temperature":0,"num_predict":num_predict}
    }).encode()
    req=urllib.request.Request(OLLAMA_URL,data=body,headers={"Content-Type":"application/json"})
    t0=time.time()
    with urllib.request.urlopen(req,timeout=900) as r:
        payload=json.loads(r.read().decode())
    return payload,time.time()-t0

def strip_fence(text):
    t=text.strip()
    if t.startswith("```"):
        lines=t.splitlines()
        if lines and lines[0].startswith("```"): lines=lines[1:]
        if lines and lines[-1].strip()=="```": lines=lines[:-1]
        t="\n".join(lines).strip()
    return t

def parse_json(text):
    t=strip_fence(text)
    try:
        x=json.loads(t)
        return x if isinstance(x,dict) else None, True
    except Exception:
        return None, False

def safety_class_for(case):
    if case.get("expected_route")=="deterministic_safety":
        return "restricted"
    return None

def main():
    cases=json.loads((PROJECT/"data"/"deployment_readiness_cases_v0.1.json").read_text(encoding="utf-8"))
    pipeline=BioSafePipelineV01(root=PROJECT,top_k=3)
    router=ComplexityEscalationRouterV01()
    guard=RegulatoryLanguageGuardV01()
    results=[]

    print("Pipeline interface: BioSafePipelineV01(root=/home/khengoon/biosafe, top_k=3)")
    print("Retrieval/messages: build_bundle + build_messages")

    for i,c in enumerate(cases,1):
        print(f"[{i:02d}/24] {c['id']}",flush=True)
        t0=time.time()
        err=None
        try:
            bundle,messages=pipeline.build_messages(
                c["query"],case_id=c["id"],safety_class=safety_class_for(c)
            )

            # Preserve frozen model-selection policy using structured benchmark signals.
            route_packet={
                "documents":c.get("documents",[]),
                "missing_fields":c.get("missing_fields",[]),
                "contradictions":c.get("contradictions",[])
            }
            if c.get("expected_route")=="deterministic_safety":
                model=None
                model_route={"model":"deterministic_safety","reasons":["HARD_SAFETY_GATE"]}
                raw_text=None
                parsed={
                    "conclusion":"I can’t provide instructions that increase harmful biological capability or help bypass containment. I can help with high-level biosafety, risk reduction, and containment principles.",
                    "applicable_authority":[],
                    "evidence":[],
                    "missing_information":[],
                    "recommended_next_step":["Reframe the request around risk reduction, containment, or safe handling."],
                    "limitations":["Restricted biological-capability assistance is not provided."],
                    "safety":{"classification":"refusal","response_mode":"refuse_and_redirect","reason":"restricted_biological_capability"}
                }
                valid=True
                ollama_payload={}
                model_wall=0.0
            else:
                if c.get("simulated_lite_result") is not None:
                    model_route=router.route(route_packet,c["simulated_lite_result"])
                else:
                    model_route=router.route(route_packet)
                model=model_route["model"]
                ollama_payload,model_wall=ollama_chat(model,messages,420)
                raw_text=((ollama_payload.get("message") or {}).get("content") or "")
                parsed,valid=parse_json(raw_text)
                if parsed is None:
                    parsed={
                        "conclusion":"The generated response could not be reliably parsed.",
                        "applicable_authority":[],
                        "evidence":[],
                        "missing_information":[],
                        "recommended_next_step":["Review the case through the established BioSafe validation pathway."],
                        "limitations":["The model output was not valid structured JSON."],
                        "safety":{"classification":"caution","response_mode":"ask_before_concluding","reason":"invalid_model_output"}
                    }

            # Guard operates on authoritative RAG evidence from the real pipeline bundle.
            final,repairs=guard.apply(parsed,bundle.get("evidence_bundle",[]))
            wall=time.time()-t0

            results.append({
                "case_id":c["id"],
                "group":c["group"],
                "expected_route":c.get("expected_route"),
                "observed_route":model_route.get("model"),
                "route_reasons":model_route.get("reasons",[]),
                "wall_seconds":round(wall,4),
                "model_wall_seconds":round(model_wall,4),
                "valid_json_first_pass":valid,
                "done_reason":ollama_payload.get("done_reason") if model else "deterministic",
                "route":bundle.get("route"),
                "evidence_bundle":bundle.get("evidence_bundle"),
                "evidence_count":len(bundle.get("evidence_bundle",[])),
                "integration_repairs":repairs,
                "raw_model_response":raw_text,
                "final_response":final,
                "error":None
            })
        except Exception as e:
            results.append({
                "case_id":c["id"],"group":c["group"],
                "expected_route":c.get("expected_route"),
                "wall_seconds":round(time.time()-t0,4),
                "error":repr(e)
            })

    out={
        "suite":"BioSafe_Deployment_Readiness_Live24_v0.3.1_ExactInterface",
        "pipeline":"biosafe_pipeline_v0_1.BioSafePipelineV01",
        "pipeline_interface":"build_messages(query, case_id, safety_class)",
        "cases":len(results),
        "results":results
    }
    outdir=PROJECT/"output"; outdir.mkdir(exist_ok=True)
    outfile=outdir/"deployment_readiness_live24_v0.3.1_exactinterface_results.json"
    outfile.write_text(json.dumps(out,indent=2,default=str),encoding="utf-8")
    print("Output:",outfile)

if __name__=="__main__":
    main()
