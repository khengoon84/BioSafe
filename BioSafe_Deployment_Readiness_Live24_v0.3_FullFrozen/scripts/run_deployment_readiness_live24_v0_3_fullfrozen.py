
from __future__ import annotations
import json, sys, time, importlib, inspect
from pathlib import Path

PROJECT = Path("/home/khengoon/biosafe")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT/"src"))

CASES = PROJECT/"data"/"deployment_readiness_cases_v0.1.json"

CANDIDATES = [
    ("pipeline_v0_1", ["BioSafePipelineV01","BioSafePipeline","run_case","run_query","process"]),
    ("biosafe_pipeline_v0_1", ["BioSafePipelineV01","BioSafePipeline","run_case","run_query","process"]),
    ("local_llm_pipeline_v0_1", ["BioSafeLocalLLMPipelineV01","BioSafePipelineV01","run_case","run_query"]),
    ("deployment_inference_integration_v0_1", ["BioSafeDeploymentInferenceIntegrationV01"]),
]

def resolve_symbol():
    errors=[]
    for module_name, symbols in CANDIDATES:
        try:
            mod=importlib.import_module(module_name)
        except Exception as e:
            errors.append(f"{module_name}: import failed: {e}")
            continue
        for s in symbols:
            if hasattr(mod,s):
                return module_name,s,getattr(mod,s),errors
    return None,None,None,errors

def maybe_instantiate(obj):
    if inspect.isclass(obj):
        return obj()
    return obj

def invoke_pipeline(target, case):
    """
    Tries common interfaces but never substitutes a fake/simplified inference path.
    """
    payload = {
        "query": case["query"],
        "user_input": case["query"],
        "documents": case.get("documents", []),
        "missing_fields": case.get("missing_fields", []),
        "contradictions": case.get("contradictions", []),
        "benchmark_case": case,
    }

    methods = []
    if callable(target):
        methods.append(target)
    for name in ["run_case","run_query","process","run","answer","generate"]:
        if hasattr(target,name) and callable(getattr(target,name)):
            methods.append(getattr(target,name))

    last_errors=[]
    for fn in methods:
        sig=None
        try:
            sig=inspect.signature(fn)
        except Exception:
            pass

        attempts = [
            ((case,), {}),
            ((case["query"],), {}),
            ((), {"case":case}),
            ((), {"query":case["query"]}),
            ((), {"user_input":case["query"]}),
            ((), payload),
        ]

        for args,kwargs in attempts:
            try:
                return fn(*args,**kwargs), fn
            except TypeError as e:
                last_errors.append(f"{getattr(fn,'__name__',str(fn))}: {e}")
                continue

    raise RuntimeError(
        "Resolved a candidate pipeline symbol but could not call it with supported interfaces.\n"
        + "\n".join(last_errors[-10:])
    )

def normalize_result(raw):
    """
    Preserve real pipeline output. Only wraps it for benchmark bookkeeping.
    """
    if isinstance(raw, tuple) and len(raw)==2 and isinstance(raw[0],dict):
        raw=raw[0]
    if hasattr(raw,"model_dump"):
        raw=raw.model_dump()
    elif hasattr(raw,"dict") and callable(raw.dict):
        raw=raw.dict()
    elif not isinstance(raw,(dict,list,str,int,float,bool,type(None))):
        raw={"repr":repr(raw)}
    return raw

def extract_final_response(raw):
    if not isinstance(raw,dict):
        return raw
    for key in ["final_response","response","assembled_response","output","answer"]:
        if key in raw:
            return raw[key]
    return raw

def extract_route(raw):
    if not isinstance(raw,dict):
        return None
    for key in ["model","selected_model","route","model_name"]:
        if key in raw:
            return raw[key]
    for key in ["routing","route_info","decision","metadata","audit"]:
        v=raw.get(key)
        if isinstance(v,dict):
            for kk in ["model","selected_model","route","model_name"]:
                if kk in v:
                    return v[kk]
    return None

def extract_bool(raw,*keys):
    if not isinstance(raw,dict): return None
    for k in keys:
        if k in raw and isinstance(raw[k],bool):
            return raw[k]
    return None

def main():
    if not CASES.exists():
        raise SystemExit(f"Missing benchmark cases: {CASES}")

    module_name,symbol_name,obj,errors = resolve_symbol()
    if obj is None:
        print("Could not resolve a real BioSafe pipeline entrypoint.")
        print("Tried:")
        for e in errors:
            print(" -",e)
        print("\nThis runner intentionally refuses to fall back to a simplified surrogate.")
        print("Please upload the project tree/listing or the current pipeline runner so the adapter can target the exact entrypoint.")
        raise SystemExit(2)

    target=maybe_instantiate(obj)
    cases=json.loads(CASES.read_text(encoding="utf-8"))
    results=[]

    print(f"Resolved pipeline: {module_name}.{symbol_name}",flush=True)

    for i,c in enumerate(cases,1):
        print(f"[{i:02d}/24] {c['id']}",flush=True)
        t0=time.time()
        try:
            raw,fn=invoke_pipeline(target,c)
            err=None
        except Exception as e:
            raw=None
            fn=None
            err=repr(e)
        wall=time.time()-t0

        norm=normalize_result(raw)
        final=extract_final_response(norm)
        results.append({
            "case_id":c["id"],
            "group":c["group"],
            "expected_route":c.get("expected_route"),
            "pipeline_module":module_name,
            "pipeline_symbol":symbol_name,
            "pipeline_callable":getattr(fn,"__name__",None) if fn else None,
            "wall_seconds":round(wall,4),
            "error":err,
            "observed_route":extract_route(norm),
            "valid_json_first_pass":extract_bool(norm,"valid_json_first_pass","compact_model_json_valid","valid_json"),
            "raw_pipeline_result":norm,
            "final_response":final
        })

    out={
        "suite":"BioSafe_Deployment_Readiness_Live24_v0.3_FullFrozen",
        "pipeline_module":module_name,
        "pipeline_symbol":symbol_name,
        "cases":len(results),
        "results":results
    }
    outdir=PROJECT/"output"
    outdir.mkdir(exist_ok=True)
    outfile=outdir/"deployment_readiness_live24_v0.3_fullfrozen_results.json"
    outfile.write_text(json.dumps(out,indent=2,default=str),encoding="utf-8")
    print("Output:",outfile)

if __name__=="__main__":
    main()
