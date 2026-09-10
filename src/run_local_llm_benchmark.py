
from __future__ import annotations
from pathlib import Path
import argparse,json,sys,time
from biosafe_pipeline_v0_1 import BioSafePipelineV01,load_benchmark
from model_adapters import TransformersLocalAdapter,OpenAICompatibleLocalAdapter

ROOT=Path(__file__).resolve().parent.parent

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--adapter",choices=["transformers","local-api"],required=True)
    ap.add_argument("--model-path")
    ap.add_argument("--base-url",default="http://127.0.0.1:8000/v1")
    ap.add_argument("--model",default="local-model")
    ap.add_argument("--limit",type=int,default=50)
    ap.add_argument("--output",default=str(ROOT/"output/model_generations_v0.1.jsonl"))
    args=ap.parse_args()

    if args.adapter=="transformers":
        if not args.model_path: ap.error("--model-path is required for transformers")
        model=TransformersLocalAdapter(args.model_path)
    else:
        model=OpenAICompatibleLocalAdapter(args.base_url,args.model)

    pipe=BioSafePipelineV01(ROOT,3)
    cases=load_benchmark(ROOT/"data/BioSafe_Benchmark_Dataset_v0.1.jsonl")[:args.limit]
    out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)

    with out.open("w",encoding="utf-8") as f:
        for c in cases:
            bundle,messages=pipe.build_messages(c["user_input"],c["id"],c["safety_class"])
            st=time.perf_counter()
            raw=model.generate(messages)
            latency=time.perf_counter()-st
            rec={"case_id":c["id"],"model_id":model.model_id,"latency_seconds":latency,
                 "route":bundle["route"],"evidence_ids":[x["evidence_id"] for x in bundle["evidence_bundle"]],
                 "raw_output":raw}
            try:
                rec["parsed_output"]=json.loads(raw)
                rec["valid_json"]=True
            except Exception as e:
                rec["valid_json"]=False
                rec["parse_error"]=str(e)
            f.write(json.dumps(rec,ensure_ascii=False)+"\n")
            print(c["id"],"valid_json=",rec["valid_json"],"latency=",round(latency,2))

if __name__=="__main__":
    main()
