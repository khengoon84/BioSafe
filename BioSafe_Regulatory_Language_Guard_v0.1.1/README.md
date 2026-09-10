# BioSafe Regulatory Language Guard v0.1.1

Narrow semantic-repair patch only. Escalation Router v0.1 and the frozen BioSafe core are unchanged.

## Copy
```bash
python scripts/install_regulatory_language_guard_v0_1_1.py --project-root /home/khengoon/biosafe
```

## Preflight
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_regulatory_language_guard_v0_1_1.py
```

## Semantic regression
```bash
python scripts/run_regulatory_language_guard_semantic_regression_v0_1_1.py
```
Expected: 5/5.

## Original component regression
```bash
python scripts/run_regulatory_guard_escalation_regression_v0_1.py
```
Expected: 11/11.

## Deployment E2E regression
```bash
python scripts/run_deployment_inference_e2e_regression_v0_1.py
```
Expected: 6/6.

If all three pass in the actual BioSafe project environment, the guard/router layer is ready for formal freeze.
