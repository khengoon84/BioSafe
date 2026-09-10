# BioSafe Qwen3.5-0.8B Full 16-Case Lite Comparison v0.1

This package runs Qwen3.5-0.8B over the same 16 context-aware document cases used for the calibrated 2B evaluation.

The architecture remains frozen. The compact envelope is the accepted Lite configuration.

## Copy files

```bash
python scripts/install_qwen3_5_0_8b_16case_lite_comparison_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_qwen3_5_0_8b_16case_lite_comparison_v0_1.py
```

## Run all 16 cases

```bash
python scripts/run_qwen3_5_0_8b_16case_lite_comparison_v0_1.py \
  --models qwen3.5:0.8b \
  --output-dir output/qwen3_5_0_8b_16case_lite_comparison_v0_1
```

## Audit

```bash
python scripts/audit_qwen3_5_0_8b_16case_lite_comparison_v0_1.py \
  output/qwen3_5_0_8b_16case_lite_comparison_v0_1/structured_context_doc_qwen3.5_0.8b.jsonl
```

Upload the Lite JSONL, summary and audit JSON. The already-completed 2B JSONL can then be paired with it for a blinded case-by-case comparison.

The package also contains `build_blinded_0_8b_vs_2b_comparison_v0_1.py` for reproducible A/B blinding.
