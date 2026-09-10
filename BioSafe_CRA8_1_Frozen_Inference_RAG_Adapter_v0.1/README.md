# BioSafe CRA-8.1 — Frozen Inference/RAG Adapter v0.1

This package connects CRA-8's domain callback boundary to the existing validated frozen inference service **without editing that service**.

## Verified live interface

```python
BioSafeFullInferenceServiceV011.infer(
    query: str,
    documents: list[dict] | None = None,
    workflow: str = "ask",
)
```

Target file:
`/home/khengoon/biosafe/src/full_inference_service_v0_1.py`

## Adapter behavior

- preserves the original current question;
- forwards structured documents;
- preserves `ask`, `review`, and `form-e` workflows;
- never calls the frozen service when CRA-3 says `skip_rag`;
- requires retrieval-request domains to match the CRA Task Frame;
- performs conservative source-ID domain-leakage checks;
- enforces the frozen response schema;
- preserves the frozen response and adds only `_cra_adapter` metadata.

## Deliberate non-changes

- no edits to the frozen Stage 8/9 inference modules;
- no query rewriting;
- no live Flask/UI replacement yet;
- no claim that the frozen retriever is internally domain-constrained.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_CRA8_1_Frozen_Inference_RAG_Adapter_v0.1
python scripts/install_cra8_1_v0_1.py
```

## Deterministic test

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra8_1_frozen_adapter_v0_1.py
```

## Optional live smoke

After deterministic tests pass and Ollama is running:

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_smoke_cra8_1_frozen_adapter_v0_1.py
```

## Next step

If deterministic and live smoke both pass, CRA-8.2 will add an HTTP/service bridge around the new CRA orchestration while leaving the current browser UI unchanged.
