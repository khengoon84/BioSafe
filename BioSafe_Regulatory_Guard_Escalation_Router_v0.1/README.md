# BioSafe Regulatory Guard + Escalation Router v0.1

Deployment-oriented layer following the Qwen3.5 0.8B-vs-2B evaluation.

**Model policy**
- Qwen3.5-0.8B: primary runtime
- Qwen3.5-2B: complex-case escalation runtime

**Architecture remains frozen.** This package does not alter the Structured Document Analysis Layer, KB, CFG-02, routers, Scope Gate, Policy Guard, CBM, or Deterministic Response Assembler.

## Copy into BioSafe

```bash
python scripts/install_regulatory_guard_escalation_router_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_regulatory_guard_escalation_router_v0_1.py
```

This v0.1 is intentionally narrow. It should be regression-tested before being frozen.
