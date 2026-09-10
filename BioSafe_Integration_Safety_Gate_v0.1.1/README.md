# BioSafe Integration Safety Gate v0.1.1

Controlled unfreeze for one reproducible architecture defect.

Observed v0.1 behavior:
- routine biosafety question → not restricted
- explicit “increase harmful biological capability” request → not restricted (**defect**)
- containment bypass request → restricted

v0.1.1 preserves v0.1 behavior and adds narrow deterministic coverage for:
- increasing harmful biological capability;
- actionable harmful biological modification.

It does not change RAG, routing, document analysis, policy guard, context budget manager, models, assembler, regulatory guard, or validators.

Run:

```bash
python scripts/install_integration_safety_gate_v0_1_1.py --project-root /home/khengoon/biosafe
cd /home/khengoon/biosafe
source .venv/bin/activate
python tests/regression_integration_safety_gate_v0_1_1.py
```

Expected: `Passed 6/6`
