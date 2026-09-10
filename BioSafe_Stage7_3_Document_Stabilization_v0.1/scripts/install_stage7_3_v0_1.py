#!/usr/bin/env python3
from pathlib import Path
import argparse
import shutil

NEW_SRC = [
    "document_context_evidence_filter_v0_1.py",
    "researcher_ibc_boundary_guard_v0_1.py",
    "compact_contradiction_renderer_v0_1.py",
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent.parent
    project = Path(args.project_root).expanduser().resolve()

    (project/"src").mkdir(parents=True, exist_ok=True)
    (project/"scripts").mkdir(parents=True, exist_ok=True)

    for name in NEW_SRC:
        shutil.copy2(here/"src"/name, project/"src"/name)

    shutil.copy2(
        here/"scripts"/"run_stage7_3_document_stabilization_v0_1.py",
        project/"scripts"/"run_stage7_3_document_stabilization_v0_1.py",
    )
    shutil.copy2(
        here/"tests"/"preflight_stage7_3_document_stabilization_v0_1.py",
        project/"scripts"/"preflight_stage7_3_document_stabilization_v0_1.py",
    )

    print("Stage 7.3 files copied into:", project)
    print("Frozen KB/RAG/router/scope/policy files were not modified.")

if __name__ == "__main__":
    main()
