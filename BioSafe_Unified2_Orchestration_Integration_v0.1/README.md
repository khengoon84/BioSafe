# BioSafe Unified-2 Orchestration Integration v0.1

Experimental non-UI Unified Ask BioSafe sidecar.

Ports: 8765 existing UI (untouched); 8767 CRA-8.4.1 (untouched); 8768 Unified-2 experimental sidecar.

Install from extracted folder:
`python scripts/install_unified2_v0_1.py`

Run:
`PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified2_sidecar_v0_1.py`

Deterministic test:
`/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_unified2_contract_v0_1.py`

Live smoke:
`/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_smoke_unified2_v0_1.py`

Important: v0.1 deliberately does not prepend the Behavioral Constitution to the user query. The current frozen inference interface has no separate system channel; contaminating the retrieval query would be architecturally incorrect.
