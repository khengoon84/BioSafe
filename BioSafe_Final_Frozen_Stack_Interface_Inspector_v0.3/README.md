# BioSafe Final Frozen Stack Interface Inspector v0.3

Diagnostic only; modifies no frozen component.

The previous inventory revealed that the exact installed filenames differ from several historical labels. In particular, it found `biosafe_pipeline_v0_3_2.py`, `output_normalizer_v0_3_2.py`, `output_validator_v0_2.py`, and `boundary_validator_v0_3_2.py`.

This inspector captures their exact callable interfaces plus the installed document adapters/guards.

Run:

```bash
python scripts/install_final_frozen_stack_interface_inspector_v0_3.py --project-root /home/khengoon/biosafe
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/inspect_final_frozen_stack_interfaces_v0_3.py
```

Upload:
`output/biosafe_final_frozen_stack_interface_inspection_v0.3.json`
