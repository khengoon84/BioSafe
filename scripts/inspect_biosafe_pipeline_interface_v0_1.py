
from __future__ import annotations
import inspect
import importlib
import json
import sys
from pathlib import Path

PROJECT = Path("/home/khengoon/biosafe")
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT/"src"))

MODULE = "biosafe_pipeline_v0_1"
SYMBOL = "BioSafePipelineV01"

def safe_signature(obj):
    try:
        return str(inspect.signature(obj))
    except Exception as e:
        return f"<signature unavailable: {e}>"

def main():
    mod = importlib.import_module(MODULE)
    cls = getattr(mod, SYMBOL)

    report = {
        "module": MODULE,
        "symbol": SYMBOL,
        "is_class": inspect.isclass(cls),
        "class_signature": safe_signature(cls),
        "module_file": getattr(mod, "__file__", None),
        "methods": [],
        "attributes": [],
    }

    for name, member in inspect.getmembers(cls):
        if name.startswith("__") and name not in ("__init__", "__call__"):
            continue
        if inspect.isfunction(member) or inspect.ismethoddescriptor(member):
            report["methods"].append({
                "name": name,
                "signature": safe_signature(member),
                "doc": (inspect.getdoc(member) or "")[:500]
            })
        elif not name.startswith("_"):
            report["attributes"].append({
                "name": name,
                "type": type(member).__name__,
                "repr": repr(member)[:300]
            })

    try:
        source_file = inspect.getsourcefile(cls)
        source_lines, start_line = inspect.getsourcelines(cls)
        report["source_file"] = source_file
        report["source_start_line"] = start_line
        report["source_excerpt"] = "".join(source_lines[:220])
    except Exception as e:
        report["source_error"] = repr(e)

    outdir = PROJECT/"output"
    outdir.mkdir(exist_ok=True)
    outfile = outdir/"biosafe_pipeline_v0_1_interface_inspection.json"
    outfile.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Module:", MODULE)
    print("Symbol:", SYMBOL)
    print("Class signature:", report["class_signature"])
    print("Module file:", report["module_file"])
    print("\nCallable methods:")
    for m in report["methods"]:
        print(f" - {m['name']}{m['signature']}")
    print("\nOutput:", outfile)

if __name__ == "__main__":
    main()
