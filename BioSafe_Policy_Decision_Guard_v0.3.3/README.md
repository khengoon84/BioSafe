# BioSafe Policy & Decision Guard v0.3.3

Controlled unfreeze addressing the reproducible compliance-certification defect observed in:
- DRB-MY-003
- DRB-QA-004

The patch is intentionally narrow. It adds deterministic routing to `ASSESS_NOT_CERTIFY`
for explicit certification, approval, and compliance-determination requests.

It prohibits both:
- unsupported positive verdicts (`complies`, `is compliant`)
- unsupported negative verdicts (`does not comply`, `is not compliant`)

It does not modify retrieval, routing, scope, structured document analysis, model choice,
context budgeting, response assembly, regulatory language guard, or safety gate.

Run:

```bash
python scripts/install_policy_decision_guard_v0_3_3.py --project-root /home/khengoon/biosafe
cd /home/khengoon/biosafe
source .venv/bin/activate
python tests/regression_policy_decision_guard_v0_3_3.py
```

Expected: `Passed 6/6`
