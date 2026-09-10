# BioSafe Regulatory Applicability Guard v0.1.1

This is a patch-installer revision only. The guard logic remains v0.1.

v0.1.1 replaces the brittle exact-text insertion with a flexible, structure-aware installer.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_Regulatory_Applicability_Guard_v0.1.1
python scripts/install_regulatory_applicability_guard_v0_1_1.py
```

Expected:

```text
Regulatory Applicability Guard v0.1.1: INSTALLED
Frozen Stage 8 files modified: NO
```

## Component regression

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python /home/khengoon/biosafe/BioSafe_Regulatory_Applicability_Guard_v0.1.1/tests/test_regulatory_applicability_guard_v0_1.py
```

Expected: `6/6 passed`

## Live regression

```bash
python /home/khengoon/biosafe/BioSafe_Regulatory_Applicability_Guard_v0.1.1/tests/test_regulatory_applicability_guard_live_v0_1.py
```
