# BioSafe CRA-8.3 — Full Corrected Regression v0.2

This is the final pre-UI regression gate after CRA-8.3.1.

It re-runs the complete 12-case workflow suite against the corrected sidecar at **127.0.0.1:8767** and strengthens the original acceptance criteria.

## Strengthened checks

In addition to the original 12 workflow cases, this version explicitly requires:

- referential follow-up to be `FOLLOW_UP`;
- continuity repair to preserve transport context;
- no placeholder local response for the follow-up;
- document review must not emit Form E or LMO material when those domains are inactive;
- Form E recommendations must not invent laboratory-director or biosafety-clearance workflow;
- the CRA quality guard must actually run for domain-sensitive outputs.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_CRA8_3_Full_Corrected_Regression_v0.2
python scripts/install_cra8_3_full_corrected_v0_2.py
```

## Start CRA-8.3.1 corrected sidecar

In Terminal 1:

```bash
PYTHONPATH=/home/khengoon/biosafe/cra_v1/src:/home/khengoon/biosafe/src /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/scripts/run_cra8_3_1_sidecar_v0_1.py
```

## Run final regression

In Terminal 2:

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/run_cra8_3_full_corrected_regression_v0_2.py
```

Expected:
- `Case summary: 12/12 passed`
- all assertions passed
- `CRA-8.3 Full Corrected Regression v0.2: PASS`

Report:
`/home/khengoon/biosafe/cra_v1/reports/cra8_3_full_corrected_regression_report_v0_2.json`

## Gate rule

Only after this full corrected regression passes should CRA-8.4 browser/UI binding begin.
