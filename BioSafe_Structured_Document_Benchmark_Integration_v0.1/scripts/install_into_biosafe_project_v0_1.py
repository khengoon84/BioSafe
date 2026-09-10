#!/usr/bin/env python3
from pathlib import Path
import argparse, shutil

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=str(Path.home()/"projects"/"biosafe"))
    args = ap.parse_args()
    project = Path(args.project_root).expanduser().resolve()
    here = Path(__file__).resolve().parent.parent

    (project/"src").mkdir(parents=True, exist_ok=True)
    (project/"scripts").mkdir(parents=True, exist_ok=True)
    (project/"data"/"structured_document_layer_v0_1").mkdir(parents=True, exist_ok=True)

    for p in (here/"src").glob("*.py"):
        shutil.copy2(p, project/"src"/p.name)
    for p in (here/"data"/"structured_document_layer_v0_1").glob("*.json"):
        shutil.copy2(p, project/"data"/"structured_document_layer_v0_1"/p.name)
    shutil.copy2(
        here/"scripts"/"run_structured_context_document_benchmark_v0_1.py",
        project/"scripts"/"run_structured_context_document_benchmark_v0_1.py"
    )
    shutil.copy2(
        here/"tests"/"preflight_structured_document_benchmark_v0_1.py",
        project/"scripts"/"preflight_structured_document_benchmark_v0_1.py"
    )
    print("Installed structured document benchmark integration into:", project)

if __name__ == "__main__":
    main()
