# BioSafe CRA-8.3.1 — Integration Quality Correction v0.1

This is a controlled architecture correction triggered by the CRA-8.3 regression report.

## Problems addressed

1. Referential follow-up continuity:
   - short referential turns such as `Why does that matter?` are recognized structurally;
   - the prior active domain is preserved;
   - the turn is classified as FOLLOW_UP rather than NEW_TASK.

2. Output-domain enforcement:
   - specialized Form E / LMO / transport / waste / containment material is removed when the CRA task frame explicitly excludes that domain.

3. Recommendation grounding:
   - institutional workflow recommendations such as laboratory-director/IBC clearance or approval are suppressed unless the active-domain evidence explicitly supports that action.

## What is NOT changed

- no frozen Stage 8/9 inference module is edited;
- no model configuration is changed;
- no browser/UI file is changed;
- CRA-8.2 remains available on port 8766 for rollback.

The corrected sidecar runs separately on **127.0.0.1:8767**.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_CRA8_3_1_Integration_Quality_Correction_v0.1
python scripts/install_cra8_3_1_v0_1.py
```

## Deterministic guard test

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra8_3_1_quality_guards_v0_1.py
```

## Start corrected sidecar

```bash
PYTHONPATH=/home/khengoon/biosafe/cra_v1/src:/home/khengoon/biosafe/src /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/scripts/run_cra8_3_1_sidecar_v0_1.py
```

## Live correction regression

In a second terminal:

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/run_cra8_3_1_live_regression_v0_1.py
```

Expected:
- 3/3 cases PASS;
- all assertions PASS.

Then rerun the full CRA-8.3 workflow suite against the corrected sidecar before CRA-8.4 browser binding.
