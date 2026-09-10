# BioSafe Context Budget Manager v0.2

Paired with **Deterministic Response Assembler v0.1**.

The Structured Document Analysis Layer v1.0 remains architecture-frozen.

## What changed from v0.1

Qwen3.5-0.8B no longer authors the complete BioSafe response envelope.

It generates only:

- `conclusion`
- `missing_information`
- `recommended_next_step`

BioSafe deterministically assembles:

- `applicable_authority`
- canonical `evidence`
- `limitations`
- `safety`

Lite generation is capped at 420 tokens with a much tighter response contract.

## Copy into BioSafe

```bash
python scripts/install_context_budget_manager_v0_2.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_context_budget_manager_v0_2.py
```

Expected:

```text
BioSafe Context Budget Manager v0.2 preflight: PASS
Lite compact-generation envelope: PASS
Standard profile preservation: PASS
Three-field Qwen response contract: PASS
Deterministic response assembler: PASS
Canonical authority/evidence assembly: PASS
Deterministic safety/limitation assembly: PASS
Compact reasoning recovery: PASS
```

## PROP-002 regression

```bash
python scripts/run_context_budget_manager_v0_2.py \
  --models qwen3.5:0.8b \
  --regression-only \
  --output-dir output/context_budget_manager_v0_2_qwen3_5_0_8b
```

Upload the JSONL and summary.

If PROP-002 passes, the next step is a controlled Qwen3.5-2B Standard benchmark on the frozen architecture.
