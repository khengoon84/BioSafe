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

## Typed authorization verification (C5 v0.2 additive architecture)

The candidate path also includes a universal final verifier. It does not decide
regulatory truth from model prose: generated text is an untrusted claim
candidate and is withheld unless a typed authorization concept, structured case
facts, and compatible scoped evidence support it.

- `src/authorization_ontology_v0_2.json` is the canonical C5 ontology for
  authorization concepts, synonyms, normative force, governance actions and
  actors, evidence claim types, and explicit Form E exclusions.
- `src/authorization_contracts_v0_2.py` defines provenance-sensitive facts,
  claim candidates, and verification statuses (`VERIFIED`, `INSUFFICIENT_FACTS`,
  `INSUFFICIENT_EVIDENCE`, `UNKNOWN_REGULATORY_REQUIREMENT`, and
  `CONFLICTING_EVIDENCE`).
- `src/authorization_verifier_v0_2.py` performs candidate detection, typed
  evidence matching, fail-closed unknown-concept handling, and deterministic
  assessment metadata. It runs for every generated candidate response, even
  when the input gate classified the query as `NONE` or educational.

High-stakes conclusions are renderable only for verified typed claims. Query
text marked `EXTRACTED_UNVERIFIED`, missing facts, conflicting facts,
unsupported concepts, incompatible claim types, and absent evidence cannot
authorize a positive or negative determination. The existing regex backstop
and Unified-225/2251 guards remain compatibility defense-in-depth layers, not
the source of regulatory truth. Future concepts should be added to this
ontology and adversarial corpus rather than isolated policy lists in multiple
services. Unified-225 and Unified-2251 are not migrated in this change.

The candidate-only generation payload also exposes an optional
`authorization_claim_candidates` array. This is an untrusted structured claim
channel, not an authority channel: each item must declare `kind`, `concept`,
`polarity`, `normative_force`, jurisdiction, material/technology trigger,
specific activity, `sentence`, and non-empty `evidence_ids`. The verifier checks
those IDs against evidence with required concept, polarity, scope, authority,
and currentness metadata before deterministic rendering. Positive claims need
positive requirement evidence; negative claims need explicit non-requirement or
exemption evidence. Conflicting evidence, unknown concepts, incompatible
scope, missing metadata, and absent evidence remain fail-closed. The frozen
assembler is not modified; C5 preserves this optional field through a runtime
adapter and then verifies it.

### Targeted live adversarial evidence

`reports/c5_typed_authorization_adversarial_live_v0_1.jsonl` records a fresh
candidate-service probe using the configured local Ollama runtime. Clearance
and registration claims were withheld with `FAIL_CLOSED`; the incomplete
permit query was rejected before any model call. Educational/model-dependent
responses that did not contain a normative authorization claim were recorded
as `NO_CLAIM`, not treated as evidence of a positive or negative determination.
The report is diagnostic evidence, not production acceptance; human semantic
review remains required.

### Authorization evidence readiness

`reports/authorization_evidence_readiness_v0_1.json` is generated from the
active candidate claim set without mutating it. Its current result is
`NO_REVIEWED_AUTHORIZATION_CLAIMS`: no positive or negative authorization
determination is renderable. Candidate health reports this readiness state, and
the live runner hashes the ontology, typed contracts, verifier, readiness
checker, and candidate service. Existing generic `notification`, `exemption`,
and Form E records are not reinterpreted as authorization-requirement evidence.