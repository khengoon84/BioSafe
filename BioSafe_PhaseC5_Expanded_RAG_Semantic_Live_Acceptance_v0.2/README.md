# BioSafe Phase C5 — Expanded RAG Semantic and Live Acceptance v0.2

C5 begins with an additive deterministic bridge. It compares the frozen active
KB v0.2 control path with the reviewed C3.7 candidate before any Ollama or live
sidecar execution. This package does not modify frozen modules, the active KB,
the existing port-8777 service, model configuration, or Unified-3.

Run from `/home/khengoon/biosafe`:

```text
.venv/bin/python -m unittest discover -s BioSafe_PhaseC5_Expanded_RAG_Semantic_Live_Acceptance_v0.2/tests -p 'test_*.py'
.venv/bin/python BioSafe_PhaseC5_Expanded_RAG_Semantic_Live_Acceptance_v0.2/scripts/run_c5_preflight_v0_1.py
```

## Authorization decision gate (additive, C5-only)

The candidate inference path (`src/candidate_inference_service_v0_1.py`) now
runs a deterministic authorization gate **before** any Ollama call, grounded in
a config-driven vocabulary (`src/authorization_vocabulary_v0_1.json`):

- `src/authorization_gate_v0_1.py` — deterministic intent classification
  (`AUTHORIZATION_APPLICABILITY`, `COMPLIANCE_STATUS`,
  `START_WORK_READINESS`, `CONTAINMENT_DETERMINATION`, `CLASSIFICATION`,
  `EDUCATIONAL`, `NONE`) plus rule-based fact extraction
  (jurisdiction, material/technology trigger, specific activity).
- `src/authorization_backstop_v0_1.py` — post-generation defense in depth:
  any positive permit/approval/licence/authorisation/exemption/notification
  claim in model output is preserved only when the scoped evidence
  `claim_type` explicitly supports that requirement type. The knowledge base
  has no `*_requirement` claim types, and `forme` never supports a permit
  claim, so unsupported positive claims are removed and replaced with the
  deterministic fail-closed message, with a structured audit record in `_meta`.

### Fail-closed invariant and model-call policy

For a high-stakes authorization query with missing project facts, the gate
short-circuits before inference:

- `_meta.model_called` is `false` and no Ollama call occurs.
- `safety.status` is `FAIL_CLOSED` with `INSUFFICIENT_FACTS`.
- `missing_information` lists each missing fact; neither positive nor negative
  determinations are allowed.
- Both determinations remain forbidden until facts are complete AND adequate
  reviewed authoritative evidence supports the exact claim.

### Live evidence (GRD-02, candidate path)

Corrected incremental live A/B run: `reports/c5_live_ab_report_v0_3.json`.
Candidate path: `model_called: false`, no positive permit claim,
`missing_facts` populated, `safety.status: FAIL_CLOSED`. Baseline (frozen,
port 8777) is unchanged and still emits an unsupported positive claim — the
pre-existing baseline defect is outside this C5-only correction and remains
reported by the suite aggregate (`BLOCKED_CORRECTION_REQUIRED`).

The current package intentionally stops at deterministic bridge readiness. Live
WSL2/Ollama acceptance of the remaining C5 cases is blocked until the candidate
service bridge and runtime environment are separately verified. Claim use and
live activation remain prohibited.