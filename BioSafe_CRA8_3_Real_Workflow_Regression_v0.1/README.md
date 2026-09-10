# BioSafe CRA-8.3 — Real Workflow Regression v0.1

CRA-8.3 validates the **actual CRA-8.2 sidecar over HTTP** before any browser/UI cutover.

## What it tests

12 workflow cases:
1. sidecar health;
2. identity/product help;
3. document capability help;
4. generic biosafety without specialized-domain leakage;
5. species identity does not auto-activate LMO/Form E;
6. task change to transport;
7. referential follow-up in the same session;
8. hard safety refusal;
9. no compliance/certification verdict;
10. real document-review upload;
11. researcher-facing Form E workflow;
12. session reset.

The benchmark checks architectural invariants rather than exact wording.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_CRA8_3_Real_Workflow_Regression_v0.1
python scripts/install_cra8_3_v0_1.py
```

## Run

Keep the CRA-8.2 sidecar running in Terminal 1 on `127.0.0.1:8766`.

In Terminal 2:

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/run_cra8_3_workflow_regression_v0_1.py
```

The report is written to:

```text
/home/khengoon/biosafe/cra_v1/reports/cra8_3_workflow_regression_report_v0_1.json
```

## Expected outcome

`12/12` workflow cases PASS.

If any case fails, do not patch the individual prompt first. Identify which CRA invariant failed and fix the architecture at the corresponding layer.

## After PASS

The next stage is CRA-8.4: browser/UI binding to CRA. At that point the current ChatGPT-inspired UI can be pointed at the validated CRA service path, with rollback preserved.
