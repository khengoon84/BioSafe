# BioSafe Stage 7.3.2 — Final Micro-Patch v0.1

This patch is intentionally limited to the final five-case freeze gate.

## Copy into BioSafe

```bash
python scripts/install_stage7_3_2_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_stage7_3_2_document_stabilization_v0_1.py
```

Expected:

```text
BioSafe Stage 7.3.2 preflight: PASS
Document evidence alias normalizer: PASS
Document fact precedence guard: PASS
SOURCE_ONLY_DRAFT compact renderer: PASS
```

## Run the five freeze-gate cases

```bash
python scripts/run_stage7_3_2_document_stabilization_v0_1.py \
  --models qwen3.5:0.8b \
  --regression-only \
  --output-dir output/stage7_3_2_regression_qwen3_5_0_8b_v0_1
```

Freeze-gate cases:

- PROP-002
- FORM-002
- SOP-002
- PROP-004
- FORM-004

Upload the JSONL and summary from the output folder. If the five cases pass without substantive regression, freeze the Structured Document Analysis Layer as v1.0 and proceed to the Context Budget Manager before Qwen3.5-2B evaluation.
