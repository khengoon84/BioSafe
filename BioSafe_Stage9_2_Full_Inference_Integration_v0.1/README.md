# BioSafe Stage 9.2 — Full Inference Integration v0.1

Connects the already-running Stage 9 browser shell to the frozen Stage 8 local inference architecture.

## What changes
Only product integration files are added/replaced:
- `/home/khengoon/biosafe/src/full_inference_service_v0_1.py`
- `/home/khengoon/biosafe/stage9_local_shell/app/service.py`
- `/home/khengoon/biosafe/stage9_local_shell/app/main.py`

The installer backs up the existing shell `service.py` and `main.py`.

## What does NOT change
No frozen Stage 8 component is overwritten.

## Install
```bash
python scripts/install_stage9_2_full_inference_v0_1.py --project-root /home/khengoon/biosafe
```

## Preflight
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python /path/to/BioSafe_Stage9_2_Full_Inference_Integration_v0.1/tests/preflight_stage9_2_full_inference_v0_1.py
```

Expected: `Stage 9.2 preflight: PASS`

## Smoke test
Make sure Ollama is running and both Qwen models are available, then:
```bash
python /path/to/BioSafe_Stage9_2_Full_Inference_Integration_v0.1/tests/smoke_stage9_2_full_inference_v0_1.py
```

Expected: `Stage 9.2 inference smoke test: PASS`

## Start UI
```bash
cd /home/khengoon/biosafe/stage9_local_shell
../.venv/bin/python app/main.py
```
Open `http://127.0.0.1:8765`.
