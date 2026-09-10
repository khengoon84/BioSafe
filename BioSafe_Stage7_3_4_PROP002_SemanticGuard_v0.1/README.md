# BioSafe Stage 7.3.4 — PROP-002 Semantic Guard v0.1

This is the final semantic cleanup for PROP-002.

## Copy into BioSafe

```bash
python scripts/install_stage7_3_4_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_stage7_3_4_prop002_semantic_guard_v0_1.py
```

Expected:

```text
BioSafe Stage 7.3.4 preflight: PASS
Category A/B uncertainty guard: PASS
Risk-assessment wording guard: PASS
Unsupported compliance-severity wording guard: PASS
Unsupported formal-approval recommendation guard: PASS
```

## Run only PROP-002

```bash
python scripts/run_stage7_3_4_prop002_semantic_guard_v0_1.py \
  --models qwen3.5:0.8b \
  --regression-only \
  --output-dir output/stage7_3_4_prop002_qwen3_5_0_8b_v0_1
```

Upload the resulting JSONL and summary. If this run is substantively clean, freeze the Structured Document Analysis Layer as v1.0.
