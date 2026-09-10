# BioSafe Unified-2.2.1 — Evidence Requirement Planner v0.1

This correction addresses the architectural failure found during human review of Unified-2.2 v0.1:

> Retrieve evidence according to the decision being made, not merely because a knowledge base exists.

## Ports
- 8768 — Unified-2.1 baseline
- 8769 — Unified-2.2 constitution-aware experiment
- 8770 — Unified-2.2.1 evidence-planner experiment

## Important limitation of v0.1
The planner formally defines retrieval activation and prevents regulatory pollution for deterministic product-help responses. For evidence-requiring tasks it preserves the existing frozen retrieval path while exposing the evidence plan for audit. Structure-aware source filtering is the next implementation increment after this behavioral validation.

## Install
```bash
python scripts/install_unified221_v0_1.py
```

## Planner contract
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_evidence_planner_v0_1.py
```

## Start 8770
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified221_sidecar_v0_1.py
```

## A/B test
Keep 8769 and 8770 running:
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_ab_unified221_v0_1.py
```
