# BioSafe Unified-2.2.5 — Decision Semantics, Prerequisite & Answer-Coverage Guard v0.1

Experimental port: **8776**. Existing 8775 and all frozen components remain unchanged.

## Invariants
1. Unknown != No.
2. Regulatory conclusions require prerequisite facts.
3. No positive or negative legal/compliance verdicts.
4. Exact legal citations require exact evidence provenance.
5. Multi-subject definition questions must address every requested subject or explicitly state insufficiency.
6. Sensitive refusals must use a safety rationale, not "query incomplete".

## Install
```bash
python scripts/install_unified225_v0_1.py
```

## Contract
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_unified225_contract_v0_1.py
```
Expected: **6/6 PASS**

## Start 8776
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified225_sidecar_v0_1.py
```

## A/B
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_ab_unified225_v0_1.py
```

## Strengthened semantic acceptance
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_semantic_acceptance_v0_1.py
```

Human wording, applicability and provenance review remains mandatory before freeze.
