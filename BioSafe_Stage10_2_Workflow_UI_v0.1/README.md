# BioSafe Stage 10.2 — Workflow UI v0.1

Presentation-only refinement for the existing local BioSafe shell.

Adds:
- explicit tabs for Ask BioSafe, Review a Document, and Form E Assistant;
- short workflow descriptions;
- accessible tab semantics and focus states;
- loading/status indicators;
- selected-file summary;
- Form E boundary reminder;
- mobile tab layout;
- no changes to endpoints, prompts, inference, RAG, guards, validators, or model routing.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_Stage10_2_Workflow_UI_v0.1
python scripts/install_stage10_2_workflow_ui_v0_1.py
```

Restart the app:

```bash
cd /home/khengoon/biosafe/stage9_local_shell
../.venv/bin/python app/main.py
```

## Static regression

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python /home/khengoon/biosafe/BioSafe_Stage10_2_Workflow_UI_v0.1/tests/test_stage10_2_workflow_ui_v0_1.py
```
