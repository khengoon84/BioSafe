# BioSafe CRA-4 — Structured Dependency Decision Engine v0.1

CRA-4 formalizes the rule:

**FACTS + PREREQUISITES + AUTHORITATIVE RULE → ALLOWED DECISION**

It does **not** encode organism-specific conclusions.

## Initial decision families
1. Malaysian LMO / notification applicability readiness
2. Biosafety containment assessment readiness
3. Transport requirement readiness
4. Waste requirement readiness

## Important safeguards
- Species identity cannot establish LMO/GMM status.
- `inferred` and merely `user_asserted` facts do not satisfy high-consequence prerequisites.
- A confirmed `False` value is treated as an established fact, not as missing data.
- Missing prerequisites force `insufficient_information`.
- Readiness does not equal regulatory applicability.
- A substantive decision requires authoritative evidence references.
- Risk group alone cannot establish a containment conclusion.
- Specific containment conclusions require additional context.
- Transport and waste decisions require their own domain facts.
- Disputed facts cannot satisfy prerequisites.

## Architecture note
`REQUIRES_HUMAN_REVIEW` at the readiness stage means:
> prerequisites are established, but authoritative rule/evidence evaluation must still occur.

It does **not** mean the user necessarily requires human regulatory review.

## Status
Isolated implementation. Not connected to live UI.
No frozen Stage 8/9 component is modified.

## Install
```bash
cd /home/khengoon/biosafe/BioSafe_CRA4_Dependency_Decision_Engine_v0.1
python scripts/install_cra4_v0_1.py
```

## Test
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra4_dependency_engine_v0_1.py
```
