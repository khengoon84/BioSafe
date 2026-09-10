# BioSafe Stage 7.3 — Document Stabilization v0.1

This is a **narrow stabilization patch** after the successful Stage 7.2 v0.1.1 run.

It does not change the frozen retriever, KB, routers, scope gate or policy guard.

## Three targeted fixes

1. **LMO/GMM review evidence discipline**
   - CFG-02 still retrieves exactly as before.
   - A document-context filter controls which retrieved claims are exposed to the model.
   - Clinical-specimen transport evidence is suppressed for generic LMO/GMM document reviews unless the user actually asks a clinical/transport question.
   - Original and exposed evidence IDs are logged for audit.

2. **Researcher-versus-IBC boundary**
   - A deterministic post-generation guard prevents BioSafe from telling a researcher/PI to submit, complete, provide or prepare an IBC Assessment Report.
   - The report remains IBC-only.

3. **Contradiction-heavy output stability**
   - Cross-document findings are presented compactly.
   - The model is instructed to keep evidence/recommendations/limitations short.
   - If a contradiction case is still truncated or invalid, a deterministic compact BioSafe-schema response is generated from the structured conflict findings.
   - Conflicts are surfaced, never silently reconciled.

## Install

Extract this ZIP. From inside the extracted package folder run:

```bash
python scripts/install_stage7_3_v0_1.py   --project-root /home/khengoon/biosafe
```

## Preflight first

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate

python scripts/preflight_stage7_3_document_stabilization_v0_1.py
```

Expected:

```text
BioSafe Stage 7.3 preflight: PASS
LMO evidence filter: PASS
Researcher-vs-IBC boundary: PASS
Compact contradiction fallback: PASS
```

## Then run Qwen3.5-0.8B

```bash
python scripts/run_stage7_3_document_stabilization_v0_1.py   --models qwen3.5:0.8b   --output-dir output/stage7_3_qwen3_5_0_8b_v0_1
```

Upload:

```text
output/stage7_3_qwen3_5_0_8b_v0_1/structured_context_doc_qwen3.5_0.8b.jsonl
output/stage7_3_qwen3_5_0_8b_v0_1/structured_context_document_benchmark_summary.json
```

## Success criteria

We will check that:

- `SOP-002` detects vague LMO/GMM wording **without drifting into clinical-specimen transport guidance**;
- `PROP-004` does not assign the IBC Assessment Report to the researcher/PI;
- `FORM-004` surfaces the deterministic proposal↔Form E conflicts and no longer fails solely because of output truncation;
- prior improvements in `TR-005`, `PROP-003`, `FORM-002`, `SOP-004` and `SOP-005` are preserved.

Qwen3.5-2B is deliberately **not** tested yet. After Stage 7.3 is stable, the structured layer can be frozen and a model-aware Context Budget Manager can be added before the four-model comparison.
