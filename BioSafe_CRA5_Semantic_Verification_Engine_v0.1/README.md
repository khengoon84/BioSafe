# BioSafe CRA-5 — Semantic Verification Engine v0.1

CRA-5 is the final machine-controlled quality gate before response composition.

## Verifier invariants

- **V-01 Prerequisite sufficiency**
- **V-02 Citation support / entailment**
- **V-03 Jurisdiction match**
- **V-04 Source currentness**
- **V-05 Domain activation**
- **V-06 State consistency**
- **V-07 Unknown preservation**
- **V-08 No compliance/certification/approval determination**
- **V-09 Recommendation support**
- **V-10 Current-turn relevance**

## What this prevents

Examples:
- unresolved facts becoming positive regulatory conclusions;
- evidence that is merely topically related being treated as support;
- Malaysian questions answered with another jurisdiction's rule;
- superseded evidence silently driving a conclusion;
- Form E/transport/waste appearing when the Task Frame did not activate them;
- confirmed user facts being contradicted;
- unknown LMO status becoming a stated LMO fact;
- positive or negative compliance certification;
- mandatory recommendations without evidence support;
- a referential follow-up being answered as a new standalone task.

## Important
This version uses deterministic metadata checks as a conservative verifier. Citation entailment is represented through evidence metadata (`supports_decision_types`). Later versions may add model-assisted semantic entailment, but deterministic checks remain authoritative.

## Status
Isolated implementation; not connected to the live UI.
No frozen Stage 8/9 component is modified.

## Install
```bash
cd /home/khengoon/biosafe/BioSafe_CRA5_Semantic_Verification_Engine_v0.1
python scripts/install_cra5_v0_1.py
```

## Test
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra5_semantic_verifier_v0_1.py
```
