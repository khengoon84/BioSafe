# BioSafe Pipeline Interface Inspector v0.1

Diagnostic-only package. It does not modify the frozen BioSafe inference architecture.

It inspects:

- `biosafe_pipeline_v0_1.BioSafePipelineV01`
- constructor signature
- callable methods and signatures
- module path
- a source excerpt for the class

## Copy

```bash
python scripts/install_pipeline_interface_inspector_v0_1.py \
  --project-root /home/khengoon/biosafe
```

## Run

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python scripts/inspect_biosafe_pipeline_interface_v0_1.py
```

Upload:

`output/biosafe_pipeline_v0_1_interface_inspection.json`

The next adapter will then target the exact constructor/method already present in the project.
