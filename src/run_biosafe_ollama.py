
from __future__ import annotations
from pathlib import Path
import argparse, json, sys, time, urllib.request

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"src"))
from biosafe_pipeline_v0_1 import BioSafePipelineV01, load_benchmark

DEFAULT_HOST="http://127.0.0.1:11434"

def http_json(url, payload=None, timeout=300):
    data=None if payload is None else json.dumps(payload).encode("utf-8")
    req=urllib.request.Request(url,data=data,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def check_server(host):
    try:
        return True, http_json(host.rstrip("/")+"/api/tags",None,5)
    except Exception as e:
        return False, str(e)

def installed_models(host):
    ok,obj=check_server(host)
    if not ok: return []
    out=[]
    for m in obj.get("models",[]):
        name=m.get("name") or m.get("model")
        if name: out.append(name)
    return out

def ollama_chat(host, model, messages, temperature=0.0, num_predict=700, timeout=600):
    payload={
        "model":model,
        "messages":messages,
        "stream":False,
        "format":"json",
        "options":{"temperature":temperature,"num_predict":num_predict}
    }
    return http_json(host.rstrip("/")+"/api/chat",payload,timeout)

def main():
    ap=argparse.ArgumentParser(description="Run the BioSafe benchmark against a local Ollama model.")
    ap.add_argument("--model",default="qwen3:0.6b")
    ap.add_argument("--host",default=DEFAULT_HOST)
    ap.add_argument("--limit",type=int,default=5)
    ap.add_argument("--start",type=int,default=0)
    ap.add_argument("--temperature",type=float,default=0.0)
    ap.add_argument("--num-predict",type=int,default=700)
    ap.add_argument("--timeout",type=int,default=600)
    ap.add_argument("--output")
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()

    ok,info=check_server(args.host)
    if not ok:
        print("\nERROR: Cannot reach Ollama at",args.host)
        print("Start Ollama first, then retry.")
        print("Detail:",info)
        raise SystemExit(2)

    models=installed_models(args.host)
    print("Ollama connection: OK")
    print("Installed models:",", ".join(models) if models else "(none found)")

    if args.model not in models:
        print(f"\nERROR: Model '{args.model}' is not installed.")
        print(f"Run: ollama pull {args.model}")
        raise SystemExit(3)

    if args.self_test:
        obj=ollama_chat(args.host,args.model,[{"role":"user","content":"Reply with JSON only: {\"status\":\"ok\"}"}],
                        temperature=0.0,num_predict=40,timeout=args.timeout)
        print("Self-test response:",obj.get("message",{}).get("content",""))
        return

    pipe=BioSafePipelineV01(ROOT,3)
    cases=load_benchmark(ROOT/"data/BioSafe_Benchmark_Dataset_v0.1.jsonl")
    cases=cases[args.start:args.start+args.limit]

    safe_model=args.model.replace(":","_").replace("/","_")
    out=Path(args.output) if args.output else ROOT/"output"/f"ollama_{safe_model}_{args.start}_{args.start+len(cases)-1}.jsonl"
    out.parent.mkdir(parents=True,exist_ok=True)

    print(f"\nRunning {len(cases)} BioSafe cases using {args.model}")
    print("Output:",out)
    print()

    with out.open("w",encoding="utf-8") as f:
        for idx,c in enumerate(cases,1):
            bundle,messages=pipe.build_messages(c["user_input"],c["id"],c["safety_class"])
            start=time.perf_counter()
            try:
                obj=ollama_chat(args.host,args.model,messages,args.temperature,args.num_predict,args.timeout)
                latency=time.perf_counter()-start
                content=obj.get("message",{}).get("content","")
                rec={
                    "case_id":c["id"],"model_id":args.model,"latency_seconds":round(latency,4),
                    "route":bundle["route"],
                    "evidence_ids":[x["evidence_id"] for x in bundle["evidence_bundle"]],
                    "raw_output":content,
                    "ollama_metrics":{
                        "total_duration":obj.get("total_duration"),
                        "load_duration":obj.get("load_duration"),
                        "prompt_eval_count":obj.get("prompt_eval_count"),
                        "prompt_eval_duration":obj.get("prompt_eval_duration"),
                        "eval_count":obj.get("eval_count"),
                        "eval_duration":obj.get("eval_duration")
                    }
                }
                try:
                    rec["parsed_output"]=json.loads(content)
                    rec["valid_json"]=True
                except Exception as e:
                    rec["valid_json"]=False
                    rec["parse_error"]=str(e)
                f.write(json.dumps(rec,ensure_ascii=False)+"\n")
                f.flush()
                print(f"[{idx:02d}/{len(cases):02d}] {c['id']}: JSON={'OK' if rec['valid_json'] else 'FAIL'}  {latency:.1f}s")
            except Exception as e:
                latency=time.perf_counter()-start
                rec={"case_id":c["id"],"model_id":args.model,"latency_seconds":round(latency,4),
                     "route":bundle["route"],
                     "evidence_ids":[x["evidence_id"] for x in bundle["evidence_bundle"]],
                     "generation_error":repr(e),"valid_json":False}
                f.write(json.dumps(rec,ensure_ascii=False)+"\n")
                f.flush()
                print(f"[{idx:02d}/{len(cases):02d}] {c['id']}: ERROR {e}")

    print("\nFinished.")
    print("Upload this JSONL file back to ChatGPT for formal BioSafe scoring:")
    print(out)

if __name__=="__main__":
    main()
