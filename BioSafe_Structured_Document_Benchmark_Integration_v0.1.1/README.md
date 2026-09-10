# BioSafe Stage 7.2 Integration v0.1.1

This is a corrective patch to v0.1.

The v0.1 run showed that the deterministic structured layer was producing useful
findings, but the LLM prompt included too much structured extraction data.
Qwen3.5-0.8B often reproduced that packet rather than returning the required
BioSafe response schema.

v0.1.1 keeps the same frozen benchmark, model settings, RAG, routing, scope and
policy architecture. It changes only how structured findings are presented to
the model.

## Changes

- compact structured findings only;
- no full fact/source-span dump in the LLM prompt;
- raw user documents are still included;
- explicit instruction not to reproduce the preprocessing packet;
- exact BioSafe output fields repeated as the final instruction.

## Install into the actual project

From the extracted package folder:

```bash
python scripts/install_into_biosafe_project_v0_1_1.py \
  --project-root /home/khengoon/biosafe
```

## Run Qwen3.5-0.8B

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate

python scripts/run_structured_context_document_benchmark_v0_1_1.py \
  --models qwen3.5:0.8b \
  --output-dir output/structured_doc_qwen3_5_0_8b_v0_1_1
```

Upload the resulting JSONL and summary JSON.

The v0.1 result should be treated as a diagnostic integration failure, not as
evidence that the structured architecture or Qwen3.5-0.8B became worse.
