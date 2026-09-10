# BioSafe Deployment Readiness Live24 v0.4.1 — Full Frozen Stack

This harness is built against the exact installed interfaces discovered in the BioSafe project.

It uses:
- `BioSafePipelineV032`
- Policy & Decision Guard v0.3.2
- authority-aware RAG
- Structured Document Benchmark Adapter
- document evidence merge/filter/precedence/decision guards
- Complexity/Escalation Router v0.1
- installed Context Budget Manager interface
- compact three-field Qwen generation
- Deterministic Response Assembler v0.1
- Output Normalizer v0.3.2
- Policy Shell Enforcer v0.3.2
- Regulatory Language Guard v0.1.1
- Response Budget Guard v0.1
- Output Validator v0.2
- Boundary Validator v0.3.2

No frozen component is modified.

Document-review cases use clearly labelled synthetic benchmark fixtures so the structured document layer is actually exercised.

## Copy
```bash
python scripts/install_deployment_readiness_live24_v0_4_fullfrozenstack.py --project-root /home/khengoon/biosafe
```

## Preflight
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_deployment_readiness_live24_v0_4_fullfrozenstack.py
```

## Run
```bash
python scripts/run_deployment_readiness_live24_v0_4_fullfrozenstack.py
```

Upload:
`output/deployment_readiness_live24_v0.4_fullfrozenstack_results.json`


## v0.4.1 patch
`BioSafePipelineV032.build_messages()` in the installed project returns three values.
The benchmark harness now identifies the bundle and messages by their structure instead
of assuming a two-value tuple. The optional third return value is preserved in benchmark
audit metadata. No frozen BioSafe source file is modified.
