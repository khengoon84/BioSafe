# BioSafe Stage 7.3.1 — Final Document Stabilization v0.1

This is the final narrow patch before freezing the structured document layer.

No changes are made to BioSafe KB v0.2, CFG-02, authority/query routing, Scope Gate v0.2.1, or Policy & Decision Guard v0.3.2.

## Four fixes

1. **Zero-evidence domain filter**
   - If every retrieved claim is known to be wrong-domain for the current document review, BioSafe now exposes zero RAG claims.
   - It no longer reintroduces a suppressed clinical-transport claim just to avoid an empty evidence bundle.

2. **User-document evidence namespace**
   - Source spans from user documents receive `DOC-*` IDs.
   - Regulatory knowledge-base evidence remains `CLM-*`.
   - This lets the model cite the supplied SOP/proposal/Form E without pretending the document itself is a regulatory source.

3. **Critical-missing compliance boundary**
   - Under `ASSESS_NOT_CERTIFY`, if critical review fields are missing, conclusions such as “appears aligned/compliant” are replaced with a deterministic non-certification conclusion.

4. **Schema-invalid contradiction fallback**
   - Cross-document contradiction fallback now activates when the model output is syntactically valid JSON but fails the BioSafe schema.
   - This directly targets the Stage 7.3 `FORM-004` failure mode.

## Copy into `/home/khengoon/biosafe`

Extract the ZIP. From the extracted package folder:

```bash
python scripts/install_stage7_3_1_v0_1.py   --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate

python scripts/preflight_stage7_3_1_document_stabilization_v0_1.py
```

Expected:

```text
BioSafe Stage 7.3.1 preflight: PASS
Zero-evidence domain filter: PASS
User-document DOC evidence namespace: PASS
Researcher-vs-IBC boundary: PASS
Critical-missing compliance boundary: PASS
Schema-invalid contradiction fallback: PASS
```

## Benchmark

```bash
python scripts/run_stage7_3_1_document_stabilization_v0_1.py   --models qwen3.5:0.8b   --output-dir output/stage7_3_1_qwen3_5_0_8b_v0_1
```

Upload:

```text
output/stage7_3_1_qwen3_5_0_8b_v0_1/structured_context_doc_qwen3.5_0.8b.jsonl
output/stage7_3_1_qwen3_5_0_8b_v0_1/structured_context_document_benchmark_summary.json
```

## Freeze criteria

We will freeze the structured document layer if:

- `SOP-002` has no clinical-specimen transport drift caused by wrong-domain fallback;
- document quotations use validator-safe `DOC-*` evidence IDs;
- `PROP-004` does not say the incomplete project “appears aligned/compliant”;
- `FORM-004` preserves the detected discrepancies in a valid BioSafe schema;
- earlier improvements in `TR-005`, `PROP-003`, `FORM-002`, `SOP-004`, and `SOP-005` remain intact.

After freeze, the next stage is the model-aware **Context Budget Manager**, followed by **Qwen3.5-2B** evaluation.
