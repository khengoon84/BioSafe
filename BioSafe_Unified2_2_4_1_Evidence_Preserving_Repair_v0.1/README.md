# BioSafe Unified-2.2.4.1 — Evidence-Preserving Semantic Repair v0.1

This package does two things:

1. Fixes the remaining 2.2.4 semantic-repair defect by preserving the scoped authoritative evidence through verification and repair.
2. Reviews the uploaded 202-test matrix and incorporates a curated set of high-value tests that fit the current BioSafe architecture.

## Architectural invariant

**Verification may remove unsupported meaning, but it must not destroy supported meaning required to answer the user's question.**

The verifier receives the same scoped evidence bundle used for generation. It may downgrade an unsupported institutional/regulatory predicate to a neutral evidence-supported role statement; otherwise it removes the unsupported claim. It never invents law, sections, permit requirements or approval status.

## Test-matrix decision

Uploaded tests: 202

Disposition:
{
  "KEEP_PRODUCT_VALIDATION": 17,
  "EXCLUDE_AS_WRITTEN": 4,
  "ADAPT_LATER": 19,
  "ADOPT_OR_ADAPT_CORE": 150,
  "DEFER_UNIFIED3": 12
}

The full row-by-row review is in:
`benchmark/uploaded_test_matrix_assessment.csv`

The immediate high-value additions are in:
`benchmark/curated_added_cases.csv`

## Install

```bash
python scripts/install_unified2241_v0_1.py
```

## Contract test

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_unified2241_contract_v0_1.py
```

Expected: **8/8 PASS**.

## Start experimental 8774

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified2241_sidecar_v0_1.py
```

## Regression against 8773

Keep both 8773 and 8774 running:

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_ab_unified2241_v0_1.py
```

## Curated additional acceptance cases

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_curated_acceptance_v0_1.py
```

Automated assertions are smoke checks only. Human wording, applicability and provenance review remains mandatory before freeze.
