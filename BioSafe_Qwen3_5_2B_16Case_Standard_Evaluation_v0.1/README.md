# BioSafe Qwen3.5-2B — 16-Case Standard Evaluation v0.1

This is the first controlled evaluation of **Qwen3.5-2B as the BioSafe Standard candidate**.

The Structured Document Analysis Layer v1.0 remains architecture-frozen. The evaluation uses Context Budget Manager v0.2 and Deterministic Response Assembler v0.1.

## Before running

Make sure the model is available in Ollama:

```bash
ollama list
```

You should see `qwen3.5:2b`.

If it is not present:

```bash
ollama pull qwen3.5:2b
```

## Copy evaluation files into BioSafe

```bash
python scripts/install_qwen3_5_2b_16case_standard_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_qwen3_5_2b_16case_standard_v0_1.py
```

Expected:

```text
BioSafe Qwen3.5-2B 16-case Standard preflight: PASS
Structured Document Layer v1.0 frozen: PASS
Qwen3.5-2B Standard profile: PASS
Compact reasoning contract: PASS
Deterministic Response Assembler v0.1: PASS
Canonical evidence assembly: PASS
```

## Run all 16 document cases

Do **not** add `--regression-only`.

```bash
python scripts/run_qwen3_5_2b_16case_standard_v0_1.py \
  --models qwen3.5:2b \
  --output-dir output/qwen3_5_2b_16case_standard_v0_1
```

This may take noticeably longer than the 0.8B run on a CPU-only laptop.

## Optional automatic audit

After the run finishes:

```bash
python scripts/audit_qwen3_5_2b_16case_standard_v0_1.py \
  output/qwen3_5_2b_16case_standard_v0_1/structured_context_doc_qwen3.5_2b.jsonl
```

Upload:
1. the benchmark JSONL;
2. `structured_context_document_benchmark_summary.json`;
3. the generated `_audit.json` if available.

We will then compare Qwen3.5-2B Standard with Qwen3.5-0.8B Lite and decide whether 2B earns the Standard role.
