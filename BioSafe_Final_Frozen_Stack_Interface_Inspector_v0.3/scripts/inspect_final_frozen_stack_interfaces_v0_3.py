
from __future__ import annotations
import importlib, inspect, json, sys
from pathlib import Path
PROJECT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(PROJECT)); sys.path.insert(0,str(PROJECT/"src"))

MODULES=[
 "biosafe_pipeline_v0_3","biosafe_pipeline_v0_3_1","biosafe_pipeline_v0_3_2",
 "boundary_validator_v0_3","boundary_validator_v0_3_1","boundary_validator_v0_3_2",
 "output_normalizer_v0_3_2","output_validator_v0_2",
 "response_budget_guard_v0_1",
 "document_decision_guard_v0_1","structured_document_benchmark_adapter_v0_1",
 "user_document_evidence_adapter_v0_1","document_context_evidence_filter_v0_1",
 "document_evidence_alias_normalizer_v0_1","document_fact_precedence_guard_v0_1",
 "normalized_document_profile_v0_1"
]
def sig(x):
    try:return str(inspect.signature(x))
    except Exception as e:return f"<unavailable:{e}>"
def inspect_mod(name):
    m=importlib.import_module(name)
    o={"module":name,"file":getattr(m,"__file__",None),"symbols":[]}
    for n,x in inspect.getmembers(m):
        if n.startswith("_"):continue
        if inspect.isclass(x) and getattr(x,"__module__",None)==name:
            item={"name":n,"kind":"class","signature":sig(x),"methods":[]}
            for mn,mm in inspect.getmembers(x):
                if mn.startswith("_") and mn not in ("__init__","__call__"):continue
                if callable(mm):item["methods"].append({"name":mn,"signature":sig(mm)})
            o["symbols"].append(item)
        elif inspect.isfunction(x) and getattr(x,"__module__",None)==name:
            o["symbols"].append({"name":n,"kind":"function","signature":sig(x)})
    return o
def main():
    report={"project_root":str(PROJECT),"modules":[]}
    for name in MODULES:
        try: report["modules"].append(inspect_mod(name))
        except Exception as e: report["modules"].append({"module":name,"error":repr(e)})
    out=PROJECT/"output"/"biosafe_final_frozen_stack_interface_inspection_v0.3.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("BioSafe Final Frozen Stack Interface Inspector v0.3")
    for m in report["modules"]:
        print(m["module"], "PASS" if "symbols" in m else "ERROR")
    print("Output:",out)
if __name__=="__main__":main()
