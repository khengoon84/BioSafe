# BioSafe Decision Quality Refinement v0.1

Controlled Stage 9 refinement. No frozen Stage 8 inference component is modified.

## Rules

- `DQ-MISS-001` — suppress narrow classes of missing-information items when they are not grounded in the user's scenario or an activated deterministic rule.
- `DQ-ENTITY-001` — flag apparent organism-name uncertainty for confirmation; do not silently correct the organism.
- `DQ-NEXT-001` — when BioSafe says information is insufficient, explicitly tell the user what to provide or confirm next and why those details matter.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_Decision_Quality_Refinement_v0.1
python scripts/install_decision_quality_refinement_v0_1.py
```

## Component regression

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python /home/khengoon/biosafe/BioSafe_Decision_Quality_Refinement_v0.1/tests/test_decision_quality_refinement_v0_1.py
```

Expected: `7/7 passed`

## Live regression

```bash
python /home/khengoon/biosafe/BioSafe_Decision_Quality_Refinement_v0.1/tests/test_decision_quality_refinement_live_v0_1.py
```

The live case reproduces the user-reported `Bacillus antracts` scenario and verifies:
- no unsupported Malaysian notification determination;
- LMO status requested;
- organism identity requested for confirmation;
- ungrounded transport-category request removed;
- user receives an explicit "what to provide next" instruction.
