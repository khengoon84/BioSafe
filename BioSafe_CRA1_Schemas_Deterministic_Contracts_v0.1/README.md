# BioSafe CRA-1 — Schemas & Deterministic Contracts v0.1

This is the first implementation deliverable of BioSafe Conversational Reasoning Architecture v1.0.

It defines strict contracts for:
- interaction classification
- conversation state
- case/project state
- task frames
- evidence plans
- decision nodes
- semantic verification results
- researcher response plans

It also implements generalized invariants such as:
- unknown facts cannot carry asserted values;
- product-help interactions bypass the domain pipeline;
- a domain cannot be active and inactive simultaneously;
- a decision with unsatisfied prerequisites cannot be marked supported;
- `insufficient_information` decisions must identify unresolved dependencies;
- product-help responses do not expose regulatory source references by default.

No frozen Stage 8/9 component is modified.

## Install
```bash
cd /home/khengoon/biosafe/BioSafe_CRA1_Schemas_Deterministic_Contracts_v0.1
python scripts/install_cra1_v0_1.py
```

## Test
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra1_contracts_v0_1.py
```
