# BioSafe Deployment Readiness Live24 v0.3 — Full Frozen Pipeline

This package corrects the limitation of Live24 v0.2.

It does **not** use the simplified compact-prompt surrogate. Instead, it attempts to call the real BioSafe pipeline already present in `/home/khengoon/biosafe`.

The runner deliberately stops if it cannot resolve a genuine project pipeline entrypoint. It will never silently substitute the simplified v0.2 path.

No frozen component is modified.

## Copy

```bash
python scripts/install_deployment_readiness_live24_v0_3_fullfrozen.py \
  --project-root /home/khengoon/biosafe
```

## Preflight

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_deployment_readiness_live24_v0_3_fullfrozen.py
```

## Run

```bash
python scripts/run_deployment_readiness_live24_v0_3_fullfrozen.py
```

If it resolves the pipeline successfully, upload:

`output/deployment_readiness_live24_v0.3_fullfrozen_results.json`

If it stops with `Could not resolve a real BioSafe pipeline entrypoint`, do not patch anything. Send me that terminal output; the next step will be to target the exact existing pipeline module/function in your project.
