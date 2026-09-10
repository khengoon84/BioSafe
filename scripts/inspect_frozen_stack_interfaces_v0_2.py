
from __future__ import annotations
import importlib, inspect, json, sys
from pathlib import Path

PROJECT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(PROJECT))
sys.path.insert(0,str(PROJECT/"src"))

CANDIDATES = {
  "policy_guard":[
    "policy_decision_guard_v0_3_2","policy_decision_guard_v0_3_1","policy_decision_guard_v0_3"
  ],
  "structured_document_layer":[
    "structured_document_analysis_layer_v1_0","structured_document_analysis_layer_v0_1",
    "structured_document_layer_v1_0","structured_document_layer_v0_1"
  ],
  "context_budget_manager":[
    "context_budget_manager_v0_2","context_budget_manager_v0_1"
  ],
  "response_assembler":[
    "deterministic_response_assembler_v0_1"
  ],
  "schema_normalizer":[
    "schema_normalizer_v0_3_2","schema_normalizer_v0_3_1"
  ],
  "policy_shell":[
    "policy_shell_enforcer_v0_3_2","policy_shell_enforcer_v0_3_1"
  ],
  "output_validator":[
    "output_validator_v0_1","output_validator"
  ],
  "boundary_validator":[
    "boundary_validator_v0_1","boundary_validator"
  ],
  "regulatory_guard":[
    "regulatory_language_guard_v0_1"
  ],
  "complexity_router":[
    "complexity_escalation_router_v0_1"
  ],
  "pipeline":[
    "biosafe_pipeline_v0_1"
  ]
}

def sig(x):
    try: return str(inspect.signature(x))
    except Exception as e: return f"<unavailable: {e}>"

def inspect_module(name):
    mod=importlib.import_module(name)
    out={"module":name,"file":getattr(mod,"__file__",None),"symbols":[]}
    for n,obj in inspect.getmembers(mod):
        if n.startswith("_"): continue
        if inspect.isclass(obj) and getattr(obj,"__module__",None)==name:
            item={"name":n,"kind":"class","signature":sig(obj),"methods":[]}
            for mn,m in inspect.getmembers(obj):
                if mn.startswith("_") and mn not in ("__init__","__call__"): continue
                if callable(m):
                    item["methods"].append({"name":mn,"signature":sig(m)})
            out["symbols"].append(item)
        elif inspect.isfunction(obj) and getattr(obj,"__module__",None)==name:
            out["symbols"].append({"name":n,"kind":"function","signature":sig(obj)})
    return out

def main():
    report={"project_root":str(PROJECT),"components":{}}
    for component,names in CANDIDATES.items():
        found=[]
        errors=[]
        for name in names:
            try:
                found.append(inspect_module(name))
            except Exception as e:
                errors.append({"module":name,"error":repr(e)})
        report["components"][component]={"found":found,"errors":errors}

    # Also inventory relevant src filenames to catch unexpected names.
    keys=("policy","structured","document","budget","assembler","normalizer","validator",
          "regulatory","router","pipeline","safety")
    report["relevant_src_files"]=sorted([
        p.name for p in (PROJECT/"src").glob("*.py")
        if any(k in p.name.lower() for k in keys)
    ])

    outdir=PROJECT/"output"; outdir.mkdir(exist_ok=True)
    outfile=outdir/"biosafe_frozen_stack_interface_inspection_v0.2.json"
    outfile.write_text(json.dumps(report,indent=2),encoding="utf-8")

    print("BioSafe Frozen Stack Interface Inspector v0.2")
    for component,info in report["components"].items():
        names=[x["module"] for x in info["found"]]
        print(f"{component}: {', '.join(names) if names else 'NOT FOUND BY CANDIDATE NAME'}")
    print("\nOutput:",outfile)

if __name__=="__main__":
    main()
