# BioSafe CRA-8 — Product Integration Scaffold v0.1

CRA-8 begins product integration **without yet modifying the live BioSafe Flask/browser application**.

## What v0.1 does
- Chains CRA-2 → CRA-3 for every turn.
- Adds deterministic product-help and social bypass routes.
- Produces domain-constrained retrieval requests for regulatory/scientific questions.
- Defines a clean `domain_callback` adapter boundary where the existing frozen Stage 8/9 RAG/inference pipeline will connect.
- Preserves the validated CRA state/task/evidence contracts.
- Keeps the live application untouched until this integration seam is validated.

## Why use a scaffold first?
Directly wiring all CRA components into the live application at once would make failures difficult to localize. This scaffold tests the application boundary before changing the working product.

## Install
```bash
cd /home/khengoon/biosafe/BioSafe_CRA8_Product_Integration_Scaffold_v0.1
python scripts/install_cra8_v0_1.py
```

## Test
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra8_product_integration_v0_1.py
```

## Next integration step after validation
CRA-8.1 will connect the scaffold's `domain_callback` to the existing frozen local inference/RAG service and run HTTP-level regression tests before any UI replacement.
