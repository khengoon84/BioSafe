# BioSafe Unified-2.2.4.2 — Subject-Aware Evidence Scope v0.1

The 2.2.4.1 live regression remained 20/21 because semantic repair still had no
IBC evidence available. The remaining defect is therefore evidence activation,
not repair.

## New invariant

**An explicit named institutional/governance subject may activate narrowly
relevant authoritative role/definition evidence without activating unrelated
jurisdictional or regulatory material.**

This layer wraps the validated 2.2.2 EvidenceScopeEnforcer. It:
- recognizes explicitly requested acronyms/subjects;
- may restore up to two directly matching role/function evidence items;
- does not reopen broad Malaysian law merely because the source is Malaysian;
- excludes Form E / assessment-report material unless the user actually asks about it;
- leaves the clean generic biosafety/biosecurity educational pathways unchanged.

Experimental port: **8775**. Port 8774 remains unchanged.

## Install
```bash
python scripts/install_unified2242_v0_1.py
```

## Contract
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_unified2242_contract_v0_1.py
```
Expected: **5/5 PASS**.

## Start 8775
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified2242_sidecar_v0_1.py
```

## A/B 8774 vs 8775
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_ab_unified2242_v0_1.py
```

## Curated supplemental acceptance suite
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_curated_acceptance_8775_v0_1.py
```

Do not freeze on assertion count alone. Human wording, evidence provenance,
regulatory applicability and false-refusal review remain mandatory.
