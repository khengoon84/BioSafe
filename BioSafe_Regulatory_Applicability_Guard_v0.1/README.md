# BioSafe Regulatory Applicability Guard v0.1

Adds one narrow deterministic rule:

**RAGUARD-MY-LMO-001** — BioSafe must not state that Malaysian Biosafety Act / Biosafety Regulations / Form E notification is mandatory unless LMO / modern-biotechnology trigger facts are established.

If trigger facts are unknown or negative, BioSafe changes to `ask_before_concluding` and separates LMO notification from pathogen handling, containment, transport, and other requirements.

## Install

```bash
cd /home/khengoon/biosafe/BioSafe_Regulatory_Applicability_Guard_v0.1
python scripts/install_regulatory_applicability_guard_v0_1.py
```

## Component regression

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python /home/khengoon/biosafe/BioSafe_Regulatory_Applicability_Guard_v0.1/tests/test_regulatory_applicability_guard_v0_1.py
```

Expected: `6/6 passed`

## Live regression

```bash
python /home/khengoon/biosafe/BioSafe_Regulatory_Applicability_Guard_v0.1/tests/test_regulatory_applicability_guard_live_v0_1.py
```
