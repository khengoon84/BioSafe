# BioSafe Deployment Readiness Live24 v0.2

The routing gate has passed. This package runs the same 24 representative cases with real local Qwen3.5 model calls.

- 0.8B is used for primary cases.
- 2B is used when the frozen escalation router selects it.
- Two restricted safety cases remain deterministic and do not call the model.
- Regulatory Language Guard v0.1.1 is applied after generation.
- No frozen architecture component is modified.

This is a deployment-readiness probe. It does not replace the existing authority-aware full benchmark harness.

## Copy
```bash
python scripts/install_deployment_readiness_live24_v0_2.py --project-root /home/khengoon/biosafe
```

## Run
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/run_deployment_readiness_live24_v0_2.py
```

This can take several minutes because it makes real 0.8B and 2B Ollama calls.

Upload:
`output/deployment_readiness_live24_v0.2_results.json`
