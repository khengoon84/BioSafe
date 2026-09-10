# BioSafe Unified-2.2.3 — Scoped Evidence Propagation & Semantic Claim Verification v0.1

Core invariant: **Once an Evidence Plan excludes evidence, excluded evidence remains unavailable throughout reasoning, assembly and verification.**

Unlike 2.2.2, this stage scopes the bundle immediately after frozen retrieval by wrapping `pipeline.build_messages()`. The unchanged full inference service then uses that same scoped bundle for document packet construction, compact generation, deterministic assembly, regulatory-language guard and output validation.

It also adds a conservative Semantic Claim Verifier for unsupported high-stakes institutional/regulatory characterizations.

## Install
```bash
python scripts/install_unified223_v0_1.py
```

## Contract
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_unified223_contract_v0_1.py
```
Expected: 7/7 PASS.

## Start 8772
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified223_sidecar_v0_1.py
```

## A/B
Keep 8771 and 8772 running:
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_ab_unified223_v0_1.py
```

Do not freeze from assertion count alone; human wording/provenance review is mandatory.
