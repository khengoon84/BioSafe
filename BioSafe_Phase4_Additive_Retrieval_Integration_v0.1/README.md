# BioSafe Phase C4 — Additive Retrieval Integration v0.1

Offline, deterministic A/B evaluation of the selected C3 candidate. This is
not a live sidecar and does not activate or replace the current product path.

Selected candidate: `C37_METADATA_CFG02:metadata_off`.

The frozen active KB v0.2 path remains the control. C4 does not modify frozen
retrieval, routing, safety, inference, model, active-KB, or manifest files. The
candidate is loaded from the additive C3.7 package only. Synthetic fixtures are
excluded.

Run from `/home/khengoon/biosafe`:

```text
.venv/bin/python -m unittest discover -s BioSafe_Phase4_Additive_Retrieval_Integration_v0.1/tests -p 'test_*.py'
.venv/bin/python BioSafe_Phase4_Additive_Retrieval_Integration_v0.1/scripts/run_phase4_ab_v0_1.py
```

The result can be `READY_FOR_C5_SEMANTIC_LIVE_ACCEPTANCE` or
`BLOCKED_CORRECTION_REQUIRED`. It cannot authorize production promotion,
claim use, or live activation. Any safety, provenance, routing, candidate
identity, or rollback failure reopens C3.