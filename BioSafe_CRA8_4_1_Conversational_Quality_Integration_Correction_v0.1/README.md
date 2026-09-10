# BioSafe CRA-8.4.1 Conversational Quality Integration Correction v0.1

Scope: correct live conversational-quality defects found during CRA-8.4 browser validation without modifying frozen Stage 8/9 inference/RAG components.

General invariants enforced:
1. Foundational educational questions receive concise authoritative concept answers without irrelevant regulatory missing-information scaffolding.
2. Short self-contained domain questions are not consumed as answers to stale pending clarifications.
3. High-confidence entity typos are normalized conservatively; current lexicon begins with `Bacillus anthracis` aliases observed in validation.
4. Elaboration requests reuse the previous supported answer rather than exposing retrieval/routing state.
5. Internal routing language is sanitized from user-visible answers.
6. Existing document review, Form E, policy, safety and frozen-domain adapter paths remain unchanged.

Authoritative grounding for the two foundational concept cards: KB-WHO-LBM4 (WHO Laboratory Biosafety Manual, 4th ed., 2020) and KB-WHO-BIOSEC (WHO Laboratory Biosecurity Guidance, 2024), both already present in BioSafe KB v0.2.

## Install
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
python /path/to/BioSafe_CRA8_4_1_Conversational_Quality_Integration_Correction_v0.1/scripts/install_cra8_4_1_v0_1.py
```

Then stop the current 8767 sidecar and run:
```bash
PYTHONPATH=/home/khengoon/biosafe/cra_v1/src:/home/khengoon/biosafe/src \
/home/khengoon/biosafe/.venv/bin/python \
/home/khengoon/biosafe/cra_v1/scripts/run_cra8_4_1_sidecar_v0_1.py
```

Run live regression:
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_regression_cra8_4_1_v0_1.py
```

Do not freeze until the live regression and browser trajectory both pass.
