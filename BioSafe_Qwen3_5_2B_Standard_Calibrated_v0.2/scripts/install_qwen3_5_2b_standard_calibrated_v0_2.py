#!/usr/bin/env python3
from pathlib import Path
import argparse, shutil

SRC_FILES = [
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

    for name in SRC_FILES:
        shutil.copy2(here/"src"/name, project/"src"/name)

    for name in [
        "run_qwen3_5_2b_standard_calibrated_v0_2.py",
        "audit_qwen3_5_2b_standard_calibrated_v0_2.py",
    ]:
        shutil.copy2(here/"scripts"/name, project/"scripts"/name)

    shutil.copy2(
        here/"tests"/"preflight_qwen3_5_2b_standard_calibrated_v0_2.py",
        project/"scripts"/"preflight_qwen3_5_2b_standard_calibrated_v0_2.py"
    )

    for name in [
        "Structured_Document_Analysis_Layer_v1.0_FREEZE.json",
        "Context_Budget_Manager_v0.2_Manifest.json",
        "Qwen3_5_2B_Standard_Calibrated_v0.2_Manifest.json",
    ]:
        shutil.copy2(here/"data"/name, project/"data"/name)

    print("Qwen3.5-2B Standard-Calibrated v0.2 files copied into:", project)
    print("Structured Document Analysis Layer v1.0 remains architecture-frozen.")
    print("CBM v0.2 + Deterministic Response Assembler v0.1 retained.")

if __name__ == "__main__":
    main()
