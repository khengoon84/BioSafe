# BioSafe Stage 7.3.3 — PROP-002 Finalization v0.1

This patch touches only the remaining PROP-002 freeze-gate issue.

## Changes

- normalized-profile fields now generate `DOC-*` evidence;
- explicit `approved courier` text is protected from contradictory generation;
- `CLM-028` cannot be inverted into a claim that clinical-specimen transport is outside the MOH guideline scope;
- unsupported advice to obtain MOH approval to classify specimens is replaced with a verification recommendation.

## Copy into BioSafe

```bash
python scripts/install_stage7_3_3_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_stage7_3_3_prop002_finalization_v0_1.py
```

Expected:

```text
BioSafe Stage 7.3.3 preflight: PASS
Normalized-profile DOC evidence: PASS
Approved-courier precedence: PASS
CLM-028 semantic consistency guard: PASS
Unsupported MOH classification-approval recommendation filter: PASS
```

## Run only PROP-002

```bash
python scripts/run_stage7_3_3_prop002_finalization_v0_1.py \
  --models qwen3.5:0.8b \
  --regression-only \
  --output-dir output/stage7_3_3_prop002_qwen3_5_0_8b_v0_1
```

Upload the JSONL and summary from that folder. If PROP-002 passes without substantive regression, freeze the Structured Document Analysis Layer as v1.0.
