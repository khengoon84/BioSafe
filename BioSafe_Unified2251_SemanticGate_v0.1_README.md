# BioSafe Unified-2.2.5.1 Semantic/Provenance Gate v0.1

## Purpose

This candidate adds a conservative post-generation semantic/provenance boundary without modifying the frozen retrieval, planner, constitution, regulatory-applicability guards, policy guards, or Stage 8/9 inference core.

It is installed alongside earlier Unified candidates. Unified-2.2.4.1 remains unchanged on port 8774; Unified-2.2.5 remains unchanged on port 8776; this candidate uses port 8777.

## Changes

- Replaces unsupported declarations that a named law does not exist with an inability-to-verify statement.
- Prevents positive or negative permit/approval/notification determinations unless explicit structured trigger facts and scoped normative evidence are both present.
- Replaces legal/compliance verdicts with a non-certification boundary.
- Prevents Form E from being represented as a permit, approval, authorization, certificate, or IBC decision.
- Prevents BioSafe from authorizing whether work may start.
- Removes exact statutory section/regulation references that are absent from the scoped evidence.
- Adds vetted deterministic answers for five stable, common educational questions.
- Adds eight dependency-free unit tests and a live semantic/provenance acceptance suite.

## Install

From WSL, place the archive in `/home/khengoon/biosafe`, then run:

```bash
cd /home/khengoon/biosafe
tar -xzf BioSafe_Unified2251_SemanticGate_v0.1.tar.gz
```

The archive adds new files only; it does not overwrite the frozen core or earlier Unified candidates.

## Static and deterministic validation

```bash
cd /home/khengoon/biosafe

.venv/bin/python -m py_compile \
  unified_v1/src/biosafe_unified2251/*.py \
  cra_v1/scripts/run_unified2251_sidecar_v0_1.py \
  cra_v1/tests/test_unified2251_semantic_gate_v0_1.py \
  cra_v1/tests/live_semantic_provenance_2251_v0_1.py

.venv/bin/python cra_v1/tests/test_unified2251_semantic_gate_v0_1.py
```

Expected deterministic result: `Ran 8 tests ... OK`.

## Start candidate service

Use a dedicated terminal:

```bash
cd /home/khengoon/biosafe
.venv/bin/python cra_v1/scripts/run_unified2251_sidecar_v0_1.py
```

The candidate listens only on `127.0.0.1:8777`.

Check health from another WSL terminal:

```bash
curl -s http://127.0.0.1:8777/health
```

Expected stage: `Unified-2.2.5.1 v0.1` and `frozen_core_modified: false`.

## Live semantic/provenance validation

With the candidate service running:

```bash
cd /home/khengoon/biosafe
.venv/bin/python cra_v1/tests/live_semantic_provenance_2251_v0_1.py
```

Then rerun the existing frozen/core and curated regression suites used for the current installation. Do not promote this candidate based only on automated assertions; review the full visible outputs for meaning and evidence support.

## Promotion gate

Do not replace the product service or begin Unified-3 until:

1. the eight deterministic tests pass;
2. the new live semantic/provenance suite passes;
3. existing frozen-stack regressions remain green;
4. the complete visible outputs receive a human semantic/provenance review;
5. no critical or high defect remains.
