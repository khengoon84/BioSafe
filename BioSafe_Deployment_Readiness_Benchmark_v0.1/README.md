# BioSafe Deployment Readiness Benchmark v0.1

24 representative deployment cases for the now-frozen BioSafe inference architecture.

This first gate validates routing and deployment-policy behavior without modifying any frozen component.

## Copy
```bash
python scripts/install_deployment_readiness_benchmark_v0_1.py --project-root /home/khengoon/biosafe
```

## Preflight
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/preflight_deployment_readiness_benchmark_v0_1.py
```

## Run routing gate
```bash
python scripts/run_deployment_readiness_routing_gate_v0_1.py
```

Expected:
```text
Cases: 24
PASS: 24
FAIL: 0
```

Upload:
`output/deployment_readiness_routing_gate_v0.1_results.json`

After this gate passes, the next package will execute the same 24 cases through the actual frozen inference stack and collect model/latency/semantic results.
