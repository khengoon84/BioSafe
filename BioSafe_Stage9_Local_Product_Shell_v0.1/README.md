# BioSafe Stage 9 — Local Product Shell v0.1

Purpose: wrap the frozen Stage 8 BioSafe architecture in a small local browser application.

Initial workflows:
1. Ask BioSafe
2. Review a Document
3. Form E Assistant

Important boundary:
- This package does not modify the frozen inference architecture.
- It connects to the installed Safety Gate v0.1.2, Policy Guard v0.3.3, and BioSafePipelineV032.
- v0.1 deliberately establishes the product shell and request boundary first.
- The validated full inference execution adapter is the next integration step.

## Install

```bash
python scripts/install_stage9_local_product_shell_v0_1.py --project-root /home/khengoon/biosafe
cd /home/khengoon/biosafe/stage9_local_shell
../.venv/bin/pip install -r requirements.txt
```

## Preflight

From the extracted package:

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python /path/to/BioSafe_Stage9_Local_Product_Shell_v0.1/tests/preflight_stage9_local_shell_v0_1.py
```

## Run

```bash
cd /home/khengoon/biosafe/stage9_local_shell
../.venv/bin/python app/main.py
```

Open:

`http://127.0.0.1:8765`

## Next Stage 9 increment

Wire the UI endpoints to the exact validated Stage 8 inference execution path:
Safety Gate → Policy Guard → RAG → Structured Document Analysis → Escalation Router → CBM → Qwen → Deterministic Assembler → Regulatory Guard → Validators.
