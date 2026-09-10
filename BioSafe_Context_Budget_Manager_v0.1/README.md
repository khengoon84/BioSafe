# BioSafe Context Budget Manager v0.1

The **Structured Document Analysis Layer v1.0 is now architecture-frozen**.

Context Budget Manager v0.1 controls how much evidence, structured findings and output capacity are allocated to each Qwen3.5 deployment profile. It does not change CFG-02, routing, scope, policy, or the frozen structured-document architecture.

## Profiles

**Lite — Qwen3.5-0.8B**
- target BioSafe prompt budget: 16K
- hard engineering prompt budget: 24K
- output budget: 700
- maximum 3 RAG claims
- maximum 6 document evidence items

**Standard — Qwen3.5-2B**
- target BioSafe prompt budget: 32K
- hard engineering prompt budget: 64K
- output budget: 900
- maximum 5 RAG claims
- maximum 10 document evidence items

These are engineering targets, not model context limits.

## Copy into BioSafe

```bash
python scripts/install_context_budget_manager_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_context_budget_manager_v0_1.py
```

Expected:

```text
BioSafe Context Budget Manager v0.1 preflight: PASS
Model-specific Lite/Standard profiles: PASS
Evidence budgeting: PASS
Structured-finding compaction: PASS
Response budget contract: PASS
Post-generation response cap: PASS
Prompt budget audit: PASS
```

## First regression — Qwen3.5-0.8B / PROP-002

```bash
python scripts/run_context_budget_manager_v0_1.py \
  --models qwen3.5:0.8b \
  --regression-only \
  --output-dir output/context_budget_manager_qwen3_5_0_8b_v0_1
```

Upload the JSONL and summary. This run tests whether the compact output contract eliminates the previous PROP-002 truncation while preserving the frozen evidence/document behavior.

After this passes, proceed to the controlled Qwen3.5-2B Standard benchmark.
