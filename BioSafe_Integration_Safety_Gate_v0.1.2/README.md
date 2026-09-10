# BioSafe Integration Safety Gate v0.1.2

This supersedes v0.1.1.

The v0.1.1 wrapper used an empty `SafetyDecision()` constructor, but the installed class requires:

`SafetyDecision(restricted, reason, matched)`

v0.1.2 fixes only that interface mismatch. The intended deterministic safety coverage is unchanged.

Run:

```bash
python scripts/install_integration_safety_gate_v0_1_2.py --project-root /home/khengoon/biosafe
cd /home/khengoon/biosafe
source .venv/bin/activate
python tests/regression_integration_safety_gate_v0_1_2.py
```

Expected:

`Passed 6/6`
