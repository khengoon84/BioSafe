#!/usr/bin/env python3
from pathlib import Path
import argparse, shutil

FILES = [
    "document_context_evidence_filter_v0_1.py",
    "researcher_ibc_boundary_guard_v0_1.py",
    "compact_contradiction_renderer_v0_1.py",
    "user_document_evidence_adapter_v0_1.py",
    "critical_missing_compliance_guard_v0_1.py",
    "document_evidence_alias_normalizer_v0_1.py",
    "document_fact_precedence_guard_v0_1.py",
    "source_only_draft_renderer_v0_1.py",
    "retrieved_claim_semantic_guard_v0_1.py",
    "clinical_proposal_semantic_guard_v0_1.py",
    "evidence_binding_guard_v0_1.py",
    "context_budget_manager_v0_1.py",
    "response_budget_guard_v0_1.py",
    "deterministic_response_assembler_v0_1.py",
    "compact_reasoning_recovery_v0_1.py",
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    args = ap.parse_args()
    here = Path(__file__).resolve().parent.parent
    project = Path(args.project_root).expanduser().resolve()
    (project/"src").mkdir(parents=True, exist_ok=True)
    (project/"scripts").mkdir(parents=True, exist_ok=True)
    (project/"data").mkdir(parents=True, exist_ok=True)

    for name in FILES:
        shutil.copy2(here/"src"/name, project/"src"/name)

    shutil.copy2(here/"scripts"/"run_context_budget_manager_v0_2.py",
                 project/"scripts"/"run_context_budget_manager_v0_2.py")
    shutil.copy2(here/"tests"/"preflight_context_budget_manager_v0_2.py",
                 project/"scripts"/"preflight_context_budget_manager_v0_2.py")
    shutil.copy2(here/"data"/"Structured_Document_Analysis_Layer_v1.0_FREEZE.json",
                 project/"data"/"Structured_Document_Analysis_Layer_v1.0_FREEZE.json")
    shutil.copy2(here/"data"/"Context_Budget_Manager_v0.2_Manifest.json",
                 project/"data"/"Context_Budget_Manager_v0.2_Manifest.json")

    print("Context Budget Manager v0.2 files copied into:", project)
    print("Deterministic Response Assembler v0.1 included.")
    print("Structured Document Analysis Layer v1.0 remains architecture-frozen.")

if __name__ == "__main__":
    main()
