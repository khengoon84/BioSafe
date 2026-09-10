# BioSafe Qwen3.5-2B Standard-Calibrated v0.2

This is the fair-comparison calibration run for Qwen3.5-2B.

The model remains Qwen3.5-2B, but its **generation envelope now matches the accepted 0.8B Lite configuration**:

- generation budget: 420 tokens
- maximum 3 RAG claims
- maximum 6 document evidence items
- maximum 3 missing-information items
- maximum 2 recommended next steps
- maximum 1 limitation
- Qwen generates only `conclusion`, `missing_information`, and `recommended_next_step`
- BioSafe deterministically assembles authority, evidence, limitations, and safety

The 2B Standard prompt/context budget remains 32K target / 64K hard engineering budget.

The Structured Document Analysis Layer v1.0 remains frozen.

## Copy into BioSafe

```bash
python scripts/install_qwen3_5_2b_standard_calibrated_v0_2.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_qwen3_5_2b_standard_calibrated_v0_2.py
```

Expected:

```text
BioSafe Qwen3.5-2B Standard-Calibrated v0.2 preflight: PASS
Structured Document Layer v1.0 frozen: PASS
2B Standard prompt budget preserved: PASS
Lite-equivalent compact reasoning envelope: PASS
Generation budget 420: PASS
Deterministic Response Assembler v0.1: PASS
Canonical evidence/authority assembly: PASS
```

## Run all 16 cases

```bash
python scripts/run_qwen3_5_2b_standard_calibrated_v0_2.py \
  --models qwen3.5:2b \
  --output-dir output/qwen3_5_2b_standard_calibrated_v0_2
```

## Audit

```bash
python scripts/audit_qwen3_5_2b_standard_calibrated_v0_2.py \
  output/qwen3_5_2b_standard_calibrated_v0_2/structured_context_doc_qwen3.5_2b.jsonl
```

Upload the JSONL, summary, and generated audit JSON.

This run is the decision gate for whether Qwen3.5-2B earns the BioSafe Standard role or whether active 2B optimization should stop.
