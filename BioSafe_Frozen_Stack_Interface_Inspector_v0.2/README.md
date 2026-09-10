# BioSafe Frozen Stack Interface Inspector v0.2

Diagnostic only. No frozen BioSafe component is modified.

It inventories the actual Python interfaces available in `/home/khengoon/biosafe/src` for:
- Policy & Decision Guard
- Structured Document Analysis
- Context Budget Manager
- Deterministic Response Assembler
- Schema Normalizer / Policy Shell
- Output and Boundary Validators
- Regulatory Language Guard
- Complexity/Escalation Router
- BioSafe pipeline

## Copy
```bash
python scripts/install_frozen_stack_interface_inspector_v0_2.py --project-root /home/khengoon/biosafe
```

## Run
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/inspect_frozen_stack_interfaces_v0_2.py
```

Upload:
`output/biosafe_frozen_stack_interface_inspection_v0.2.json`
