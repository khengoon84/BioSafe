# BioSafe Decision Quality Refinement v0.1.2

Narrow correction following live regression.

Changes:
1. `DQ-MISS-001` now recognizes the abbreviation `BSL`, so unsupported BSL-classification requests are suppressed unless containment/facility/BSL context is actually present.
2. The live regression validates observable product behavior rather than requiring transient internal `_meta` provenance, because the current Stage 9 adapter reconstructs `_meta` after the refinement step.

No Stage 8 component is changed. No integration hook is changed.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_Decision_Quality_Refinement_v0.1.2
python scripts/install_decision_quality_refinement_v0_1_2.py
```

## Component regression

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python /home/khengoon/biosafe/BioSafe_Decision_Quality_Refinement_v0.1.2/tests/test_decision_quality_refinement_v0_1_2.py
```

Expected: `9/9 passed`

## Live behavior regression

```bash
python /home/khengoon/biosafe/BioSafe_Decision_Quality_Refinement_v0.1.2/tests/test_decision_quality_refinement_live_v0_1_2.py
```
