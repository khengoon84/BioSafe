# BioSafe CRA-8.2 — HTTP/Service Bridge v0.1

CRA-8.2 exposes CRA through a **separate Flask sidecar on 127.0.0.1:8766**. The existing BioSafe browser/UI on port 8765 remains unchanged.

## Endpoints
- `GET /health`
- `POST /api/ask`
- `POST /api/review`
- `POST /api/form-e`
- `POST /api/session/reset`

## Architecture
`HTTP → session state → CRA-2 → CRA-3 → local bypass OR CRA-8.1 → frozen BioSafeFullInferenceServiceV011`

## Install
```bash
cd /home/khengoon/biosafe/BioSafe_CRA8_2_HTTP_Service_Bridge_v0.1
python scripts/install_cra8_2_v0_1.py
```

## Test 1 — service runtime
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra8_2_service_runtime_v0_1.py
```

## Test 2 — Flask HTTP contract
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra8_2_flask_http_contract_v0_1.py
```

## Live HTTP test
Terminal 1:
```bash
PYTHONPATH=/home/khengoon/biosafe/cra_v1/src:/home/khengoon/biosafe/src /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/scripts/run_cra8_2_sidecar_v0_1.py
```

Terminal 2:
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_http_smoke_cra8_2_v0_1.py
```

Expected final line: `CRA-8.2 optional live HTTP smoke: PASS`.

## Next
CRA-8.3 will run real workflow-level regression against this sidecar before any browser endpoint is switched from the current application.
