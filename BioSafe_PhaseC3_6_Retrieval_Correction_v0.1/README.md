# BioSafe Phase C3.6 — Independent Generalization v0.1

Additive, offline-only retrieval and routing diagnostics. C3.6 supersedes the
limited C3.4 generalization claim with independently authored queries, explicit
unknown-evidence cases, semantic boundary contracts, minimal-pair route cases,
and a metadata-only onboarding fixture.

This package does not modify frozen retrieval/routing modules, the active KB,
the live manifest, model configuration, or any runtime path. It does not invoke
Ollama. The report intentionally remains `BLOCKED_PENDING_OWNER_REVIEW`.

Run from `/home/khengoon/biosafe`:

```text
.venv/bin/python -m unittest discover -s BioSafe_PhaseC3_6_Retrieval_Correction_v0.1/tests -p 'test_*.py'
.venv/bin/python BioSafe_PhaseC3_6_Retrieval_Correction_v0.1/scripts/run_phase_c3_6_v0_1.py
```

The fixture under `fixtures/` is synthetic and never authoritative. Adding it
to the diagnostic corpus is a data/configuration operation; no fixture-specific
Python conditional is used.