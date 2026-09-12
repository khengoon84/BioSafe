# BioSafe Phase C3.4 — Metadata Generalization v0.1

This is an additive, offline diagnostic package. It evaluates whether reviewed
document metadata can support deterministic retrieval across held-out wording and
a metadata-only synthetic onboarding fixture. It does not modify frozen retrieval,
routing, pipeline, active knowledge-base, model, or runtime files.

The policy artifact is generated from the reviewed source policy, component map,
curated candidate claims, and document identity crosswalk. All 17 reviewed source
documents are represented in policy metadata; only reviewed claims are eligible
for evidence retrieval. The onboarding fixture is explicitly synthetic and never
authoritative.

Run:

```text
.venv/bin/python -m unittest discover -s BioSafe_PhaseC3_4_Metadata_Generalization_v0.1/tests -p 'test_*.py'
.venv/bin/python BioSafe_PhaseC3_4_Metadata_Generalization_v0.1/scripts/run_phase_c3_4_v0_1.py
```

The report intentionally remains `BLOCKED_PENDING_OWNER_REVIEW`. Held-out recall
is evidence about this finite fixture set, not accuracy for arbitrary prompts.
C4 remains gated until the owner reviews the report and safety/provenance evidence.