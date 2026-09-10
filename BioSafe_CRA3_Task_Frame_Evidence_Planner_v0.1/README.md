# BioSafe CRA-3 — Task Frame + Evidence Requirement Planner v0.1

CRA-3 controls **what BioSafe is allowed to reason about before retrieval starts**.

## Components
- Task Frame Builder v0.1
- Evidence Requirement Planner v0.1
- Retrieval Request Adapter v0.1

## Key generalized safeguards
- Product/help questions activate no regulatory domain and skip RAG.
- Generic biosafety questions do not automatically activate Form E, transport, or waste.
- Species identity alone does not activate LMO/Form E.
- Transport/waste/Form E are activated only when the current task requests them.
- Referential follow-ups inherit the active conversational domain rather than creating a new regulatory workflow.
- A follow-up with no evidence requirement can skip RAG.
- Task changes replace the active requested domain rather than mixing unrelated domains.
- Retrieval receives a domain-constrained Evidence Plan instead of relying on the raw query alone.

## Status
Isolated implementation only. Not yet connected to the live browser shell.
No frozen Stage 8/9 component is modified.

## Install
```bash
cd /home/khengoon/biosafe/BioSafe_CRA3_Task_Frame_Evidence_Planner_v0.1
python scripts/install_cra3_v0_1.py
```

## Test
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra3_task_frame_evidence_v0_1.py
```
