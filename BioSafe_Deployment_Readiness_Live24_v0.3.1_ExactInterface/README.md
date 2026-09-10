# BioSafe Deployment Readiness Live24 v0.3.1 — Exact Interface

Built from the inspected real interface:

- `BioSafePipelineV01(root=/home/khengoon/biosafe, top_k=3)`
- `build_messages(query, case_id=None, safety_class=None)`
- authority-aware retrieval and evidence bundle are produced by the existing pipeline.

No frozen BioSafe component is modified.

## Copy
```bash
python scripts/install_deployment_readiness_live24_v0_3_1_exactinterface.py --project-root /home/khengoon/biosafe
```

## Preflight
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_deployment_readiness_live24_v0_3_1_exactinterface.py
```

The preflight must explicitly say:
`Authority-aware retrieval returned evidence: PASS`

## Run
```bash
python scripts/run_deployment_readiness_live24_v0_3_1_exactinterface.py
```

Upload:
`output/deployment_readiness_live24_v0.3.1_exactinterface_results.json`
