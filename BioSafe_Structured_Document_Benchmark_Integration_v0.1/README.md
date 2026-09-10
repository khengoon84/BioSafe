# BioSafe Stage 7.2 — Structured Document Benchmark Integration v0.1

This package integrates **BioSafe Structured Document Analysis Layer v0.1**
into the existing frozen 16-case context-aware document benchmark.

## What changes

Only document pre-processing changes.

Before the Qwen model is called, BioSafe now creates a structured packet containing:

- document type;
- extracted facts;
- explicit missing fields;
- vague/ambiguous statements;
- normalized document profile;
- cross-document contradictions;
- the existing frozen RAG evidence;
- the existing policy mode.

The original raw synthetic document text is still supplied to the model.

## What does NOT change

- BioSafe Context-Aware Document Benchmark v0.2
- BioSafe KB v0.2
- CFG-02
- Integration Authority Router v0.1
- Query Router v0.2
- Scope Gate v0.2.1
- Policy & Decision Guard v0.3.2
- Output Normalizer v0.3.2
- Policy Shell Enforcer v0.3.2
- Qwen3.5-0.8B: temperature=0, think=false, num_predict=900

## Install

Unzip this package anywhere, then from the package folder:

```bash
python scripts/install_into_biosafe_project_v0_1.py
```

This copies only the new structured-document modules and runner into
`~/projects/biosafe`. It does not overwrite the frozen BioSafe pipeline.

Your existing project must already contain:

```text
~/projects/biosafe/data/BioSafe_Context_Aware_Document_Benchmark_v0.2.jsonl
~/projects/biosafe/data/context_documents_v0_2/
```

## Preflight — no model call

Run this first:

```bash
cd ~/projects/biosafe
source .venv/bin/activate

python scripts/preflight_structured_document_benchmark_v0_1.py   --project-root ~/projects/biosafe
```

Expected first line:

```text
BioSafe structured document preflight: PASS
```

The preflight specifically checks:

1. vague wording in SOP-03 is detected;
2. PROP-01 missing host/construct information is surfaced;
3. PROP-01 vs completed Form E produces cross-document conflict findings.

## Then run Qwen3.5-0.8B

```bash
python scripts/run_structured_context_document_benchmark_v0_1.py   --models qwen3.5:0.8b   --output-dir output/structured_doc_qwen3_5_0_8b_v0_1
```

Upload:

```text
structured_context_doc_qwen3.5_0.8b.jsonl
structured_context_document_benchmark_summary.json
```

We will manually audit the same priority cases:
`SOP-002`, `TR-005`, `PROP-003`, `PROP-004`, `FORM-002`, and `FORM-004`.

Only after this structured-layer run is substantively better should we run the
same architecture across Qwen3 0.6B, Qwen3 1.7B, and Qwen3.5 2B.
