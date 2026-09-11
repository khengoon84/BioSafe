# BioSafe Phase C3 — Offline Retrieval Benchmark v0.1

This package benchmarks deterministic retrieval over the Phase C2 curated candidate
claim corpus. It is additive and reference-only. It does not ingest new PDFs, alter
the live knowledge base, invoke Ollama, or activate any claim for production use.

## Scope

- 32 curated claims, each represented by a deterministic retrieval record.
- Gold queries derived from the reviewed original claim text.
- Exact support-span IDs, PDF pages, and quoted support remain attached to each case.
- CFG-01 and CFG-02 are evaluated without changing their source code.
- `REVIEW_REQUIRED_BEFORE_CLAIM_USE` and `PROHIBITED_PENDING_PHASE_C_GATES` are
  preserved in every generated artifact and report.

This first descriptive run measures retrieval behavior; it does not declare a
pass/fail threshold and does not authorize Phase C4.

## Run

```bash
cd /home/khengoon/biosafe
.venv/bin/python BioSafe_PhaseC3_Retrieval_Benchmark_v0.1/scripts/run_phase_c3_benchmark_v0_1.py
```

The script rebuilds the additive KB and manifest, evaluates the gold cases, and
writes `reports/phase_c3_retrieval_benchmark_v0_1.json`.

## Tests

```bash
.venv/bin/python -m unittest discover -s BioSafe_PhaseC3_Retrieval_Benchmark_v0.1/tests -p 'test_*.py'
```

The benchmark is not a live retrieval integration test. Controlled source review,
claim use, regulatory applicability, currentness, and safety decisions remain
separate gates.