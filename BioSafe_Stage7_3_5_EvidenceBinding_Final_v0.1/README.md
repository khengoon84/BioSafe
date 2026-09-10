# BioSafe Stage 7.3.5 — Evidence Binding Final v0.1

This is the final evidence-integrity patch before freezing the Structured Document Analysis Layer.

## Copy into BioSafe

```bash
python scripts/install_stage7_3_5_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_stage7_3_5_evidence_binding_final_v0_1.py
```

Expected:

```text
BioSafe Stage 7.3.5 preflight: PASS
Substantive DOC evidence ordering: PASS
Evidence ID-to-statement binding: PASS
Authority grounding: PASS
Duplicate repair wording cleanup: PASS
```

## Run only PROP-002

```bash
python scripts/run_stage7_3_5_evidence_binding_final_v0_1.py \
  --models qwen3.5:0.8b \
  --regression-only \
  --output-dir output/stage7_3_5_prop002_qwen3_5_0_8b_v0_1
```

Upload the JSONL and summary. If this case is clean, freeze the Structured Document Analysis Layer as v1.0.
