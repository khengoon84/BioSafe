# BioSafe Deployment Inference Integration v0.1

This package integrates the validated Regulatory Language Guard v0.1 and Complexity/Escalation Router v0.1 around the existing frozen BioSafe architecture.

It does **not** redesign the Structured Document Analysis Layer.

## Copy files

```bash
python scripts/install_deployment_inference_integration_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_deployment_inference_integration_v0_1.py
```

## End-to-end deployment regression

```bash
python scripts/run_deployment_inference_e2e_regression_v0_1.py
```

Expected:

```text
Cases: 6
PASS: 6
FAIL: 0
```

Upload `output/deployment_inference_e2e_regression_v0.1_results.json`.

If 6/6 passes in the actual project environment, Regulatory Language Guard v0.1 and Complexity/Escalation Router v0.1 can be considered ready for a freeze decision.
