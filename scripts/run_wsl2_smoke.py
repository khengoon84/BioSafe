#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, json, os, subprocess, sys, urllib.request

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))
from run_biosafe_ollama import check_server, installed_models, ollama_chat
from biosafe_pipeline_v0_1 import BioSafePipelineV01, load_benchmark

def detect_host():
    env=os.getenv("BIOSAFE_OLLAMA_HOST")
    if env and env.upper()!="AUTO":
        return env.rstrip("/")
    candidates=["http://127.0.0.1:11434"]
    try:
        gw=subprocess.check_output(
            ["sh","-lc","ip route | awk '/default/ {print $3; exit}'"],
            text=True
        ).strip()
        if gw:
            candidates.append(f"http://{gw}:11434")
    except Exception:
        pass
    for h in candidates:
        ok,_=check_server(h)
        if ok:
            return h
    return candidates[0]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model", default=os.getenv("BIOSAFE_OLLAMA_MODEL","qwen3:0.6b"))
    ap.add_argument("--limit", type=int, default=int(os.getenv("BIOSAFE_BENCHMARK_LIMIT","5")))
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--host", default=None)
    args=ap.parse_args()

    host=(args.host or detect_host()).rstrip("/")
    ok,detail=check_server(host)
    if not ok:
        print(f"ERROR: Ollama not reachable at {host}")
        print("Run: python3 scripts/detect_ollama.py")
        raise SystemExit(2)

    models=installed_models(host)
    if args.model not in models:
        print(f"ERROR: {args.model} is not installed in Ollama.")
        print(f"On Windows, run: ollama pull {args.model}")
        raise SystemExit(3)

    pipe=BioSafePipelineV01(ROOT,3)
    cases=load_benchmark(ROOT/"data/BioSafe_Benchmark_Dataset_v0.1.jsonl")
    cases=cases[args.start:args.start+args.limit]

    safe=args.model.replace(":","_").replace("/","_")
    out=ROOT/"output"/f"wsl2_{safe}_{args.start}_{args.start+len(cases)-1}.jsonl"
    out.parent.mkdir(exist_ok=True)

    print("Ollama:",host)
    print("Model:",args.model)
    print("Cases:",len(cases))
    print("Output:",out)

    import time
    with out.open("w",encoding="utf-8") as f:
        for i,c in enumerate(cases,1):
            bundle,messages=pipe.build_messages(c["user_input"],c["id"],c["safety_class"])
            st=time.perf_counter()
            try:
                obj=ollama_chat(host,args.model,messages,0.0,700,600)
                latency=time.perf_counter()-st
                content=obj.get("message",{}).get("content","")
                rec={
                    "case_id":c["id"], "model_id":args.model, "ollama_host":host,
                    "latency_seconds":round(latency,4),
                    "route":bundle["route"],
                    "evidence_ids":[x["evidence_id"] for x in bundle["evidence_bundle"]],
                    "raw_output":content,
                    "ollama_metrics":{
                        "total_duration":obj.get("total_duration"),
                        "load_duration":obj.get("load_duration"),
                        "prompt_eval_count":obj.get("prompt_eval_count"),
                        "eval_count":obj.get("eval_count")
                    }
                }
                try:
                    rec["parsed_output"]=json.loads(content); rec["valid_json"]=True
                except Exception as e:
                    rec["valid_json"]=False; rec["parse_error"]=str(e)
                print(f"[{i:02d}/{len(cases):02d}] {c['id']}: JSON={'OK' if rec['valid_json'] else 'FAIL'} {latency:.1f}s")
            except Exception as e:
                rec={"case_id":c["id"],"model_id":args.model,"ollama_host":host,
                     "generation_error":repr(e),"valid_json":False}
                print(f"[{i:02d}/{len(cases):02d}] {c['id']}: ERROR {e}")
            f.write(json.dumps(rec,ensure_ascii=False)+"\n")
            f.flush()
    print("\nDone:",out)

if __name__=="__main__":
    main()
