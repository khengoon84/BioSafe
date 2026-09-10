# BioSafe Regulatory Guard + Escalation Regression v0.1

Targeted regression suite for the deployment-oriented BioSafe guard/router layer.

It tests the exact failure classes observed in the Qwen3.5 0.8B and 2B benchmark work:

- internal Tier terminology leaking into user-facing regulatory language;
- unsupported legal-violation language;
- P620/P650 represented as transport classification;
- unsupported formal approval claims;
- preserving genuinely supported legal language;
- 0.8B default routing;
- 2B escalation for multiple documents;
- 2B escalation for contradictions;
- 2B escalation for high missing-information load;
- 2B escalation after Lite failure;
- no unnecessary escalation after a healthy Lite result.

The Structured Document Analysis Layer v1.0 remains frozen.

## Copy into BioSafe

```bash
python scripts/install_regulatory_guard_escalation_regression_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_regulatory_guard_escalation_regression_v0_1.py
```

## Run regression suite

```bash
python scripts/run_regulatory_guard_escalation_regression_v0_1.py
```

Upload `output/regulatory_guard_escalation_regression_v0.1_results.json`.
