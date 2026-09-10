# BioSafe Stage 9.3 — Product-Level End-to-End Validation v0.1

This package validates the working Stage 9.2 product integration without modifying frozen Stage 8 components.

## Regression targets

1. Normal Ask BioSafe output is parseable and recommendations are real strings.
2. Certification/approval requests preserve `ASSESS_NOT_CERTIFY`.
3. Restricted capability requests short-circuit before the model.
4. Document review does not certify compliance and does not emit source-only placeholders.
5. Form E assistance flags missing information and does not instruct the researcher to prepare an IBC Assessment Report.
6. Multi-document cases escalate to Qwen3.5-2B and complete with valid compact JSON.

## Run product regression

Make sure Ollama is running.

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate

python /home/khengoon/biosafe/BioSafe_Stage9_3_Product_E2E_Validation_v0.1/tests/run_stage9_3_product_e2e_v0_1.py
```

A detailed JSON report will be written to:

`/home/khengoon/biosafe/stage9_3_product_e2e_results.json`

## Run HTTP/UI-backend smoke test

First start the app in one terminal:

```bash
cd /home/khengoon/biosafe/stage9_local_shell
../.venv/bin/python app/main.py
```

Then, in another terminal:

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate

python /home/khengoon/biosafe/BioSafe_Stage9_3_Product_E2E_Validation_v0.1/tests/run_stage9_3_http_smoke_v0_1.py
```

Expected:

`Stage 9.3 HTTP shell smoke test: PASS`

## Freeze rule

Do not change frozen components because of wording preferences. A failure must first be classified as:
- product shell defect,
- integration adapter defect,
- regression-test issue,
- or reproducible frozen-architecture defect.

Only the last category can justify controlled unfreezing.
