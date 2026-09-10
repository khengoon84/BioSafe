# BioSafe Unified-2.2.4 — Response-Type Contract & Semantic Repair v0.1

Core invariants:
1. Response structure follows task type, not merely common schema availability.
2. Educational answers do not inherit regulatory/document-review elicitation by default.
3. When verification removes an unsupported high-stakes predicate, supported meaning should be preserved where possible.

Experimental port: 8773. Frozen retriever, planner, Behavioral Constitution, and regulatory guards are unchanged.

## Install
```bash
python scripts/install_unified224_v0_1.py
```

## Contract test
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_unified224_contract_v0_1.py
```
Expected: 9/9 PASS.

## Start
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified224_sidecar_v0_1.py
```

## A/B
Keep 8772 and 8773 running:
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_ab_unified224_v0_1.py
```

Human wording/provenance review remains mandatory before freeze.
