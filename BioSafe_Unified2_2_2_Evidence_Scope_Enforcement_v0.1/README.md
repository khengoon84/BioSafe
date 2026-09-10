# BioSafe Unified-2.2.2 — Evidence Scope Enforcement & Intent Normalization v0.1

Implements two generalized corrections without editing the frozen retriever:
1. conversational intent normalization before evidence planning;
2. post-retrieval/pre-generation evidence scope enforcement.

## Install
```bash
python scripts/install_unified222_v0_1.py
```

## Contract
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_unified222_contract_v0_1.py
```

## Start
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified222_sidecar_v0_1.py
```

## A/B
Keep 8770 and 8771 running:
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_ab_unified222_v0_1.py
```

Port 8771 is experimental. Do not freeze until hard assertions and human wording review pass.
