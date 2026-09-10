# BioSafe Decision Quality Refinement v0.1.1

Installer correction only. Decision-quality logic remains v0.1.

The v0.1 installer used over-escaped regex patterns and could not recognize the actual
Stage 9.2 adapter. v0.1.1 uses the exact anchors already confirmed in the user's current file.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_Decision_Quality_Refinement_v0.1.1
python scripts/install_decision_quality_refinement_v0_1_1.py
```

Expected:

```text
BioSafe Decision Quality Refinement v0.1.1: INSTALLED
Frozen Stage 8 files modified: NO
```

## Component regression

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python /home/khengoon/biosafe/BioSafe_Decision_Quality_Refinement_v0.1.1/tests/test_decision_quality_refinement_v0_1.py
```

Expected: 7/7 passed

## Live regression

```bash
python /home/khengoon/biosafe/BioSafe_Decision_Quality_Refinement_v0.1.1/tests/test_decision_quality_refinement_live_v0_1.py
```
