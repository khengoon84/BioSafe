# BioSafe Phase C3.7 — Retrieval Benchmark Integrity Correction v0.2

Additive, offline-only retrieval benchmark closure. C3.7 preserves the frozen
retrieval stack and active KB while correcting the C3.6 benchmark contracts,
separating metric applicability, using hash-bound support spans, and reporting
computed per-variant gates.

The package evaluates 64 independent claim queries, explicit unknown-evidence
cases, all seven baseline authority/scope boundaries, minimal-pair cases,
fail-closed conflict/currentness cases, metadata-on/off paths, and synthetic
onboarding. Fixtures and BioSafe boundary contracts are never represented as
authoritative source wording. This
package does not modify frozen retrieval/routing modules, the active KB, the
live manifest, model configuration, or any runtime path. It does not invoke
Ollama.

Run from `/home/khengoon/biosafe`:

```text
.venv/bin/python -m unittest discover -s BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_v0.2/tests -p 'test_*.py'
.venv/bin/python BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_v0.2/scripts/run_phase_c3_7_v0_2.py
```

`machine_gate_result` is computed from hard gates. A development candidate does
not close C3: the package has no independently authored locked holdout. The
report remains
`BLOCKED_PENDING_OWNER_REVIEW`, and live activation remains
`PROHIBITED_PENDING_PHASE_C_GATES`, regardless of deterministic results.

This is evidence about a finite fixture set, not a claim of arbitrary-prompt
accuracy or production readiness. Owner semantic and provenance review is
required before any C4 additive integration decision.

## Current deterministic result

The finite development suite identifies `C37_METADATA_CFG02:metadata_off` as
the only eligible development candidate. CFG01 misses one independent case
with metadata off; metadata on harms measured ranks and is not eligible. The
top-level result remains `BLOCKED_HOLDOUT_AND_OWNER_REVIEW` because no
independently authored locked holdout has been run.

Currentness and conflict fixtures establish conservative abstention when the
jurisdiction or authoritative resolution is unavailable. They do not establish
resolution between verified competing authoritative versions. Source diversity
and duplicate domination are reported descriptively; no threshold is promoted
without an independently justified benchmark contract.

## Provisional non-independent stress run

`data/provisional_stress_cases_v0_1.json` was agent-authored after candidate
inspection at SHA-256
`087e48c805752d1915773cea03fd332d159f04b2881a369068aca51a236c6a0c`.
It is explicitly `PROVISIONAL_NON_INDEPENDENT_NOT_A_C3_CLOSURE_GATE`.
Only the predeclared `C37_METADATA_CFG02:metadata_off` candidate is run:

```text
.venv/bin/python BioSafe_PhaseC3_7_Retrieval_Benchmark_Closure_v0.2/scripts/run_provisional_stress_v0_1.py
```

The 21-case provisional run passes its deterministic checks, but C3 remains
blocked pending a genuinely independent holdout and owner review. The generated
`reports/provisional_owner_review_packet_v0_1.json` is hash-bound to the stress
report and intentionally leaves all human decision fields blank. Review should
pay particular attention to acceptable evidence appearing at ranks 5–9 in
`C37-PS-003`, `C37-PS-007`, `C37-PS-B01`, `C37-PS-B04`, and `C37-PS-B07`.