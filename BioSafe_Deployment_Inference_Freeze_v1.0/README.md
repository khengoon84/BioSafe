# BioSafe Deployment Inference Freeze v1.0

This package formally freezes:

- Regulatory Language Guard v0.1.1
- Complexity/Escalation Router v0.1

Model policy:
- Qwen3.5-0.8B = primary
- Qwen3.5-2B = escalation

The Structured Document Analysis Layer v1.0 and previously frozen core remain unchanged.

## Copy freeze records into BioSafe

```bash
python scripts/install_deployment_inference_freeze_v1_0.py \
  --project-root /home/khengoon/biosafe
```

## Verify freeze

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/verify_deployment_inference_freeze_v1_0.py
```

This package also contains the specification for the next stage:

**BioSafe Deployment Readiness Benchmark v0.1 — 24 representative cases.**
