# BioSafe Phase C3.3 — Retrieval Oracle and Candidate Diagnostics v0.1

C3.3 corrects the retrieval benchmark oracle. It preserves C3, C3.1, and C3.2
unchanged and remains offline/additive. It does not modify the live KB, frozen
retrievers, router, pipeline, models, or activation state.

The dataset distinguishes tightly scoped canonical cases, broad multi-relevant
cases, and semantic boundary cases. Boundary cases do not incorrectly forbid the
very evidence needed to explain a boundary such as “Form E is not approval.”

Run:

```bash
cd /home/khengoon/biosafe
.venv/bin/python BioSafe_PhaseC3_3_Retrieval_Oracle_v0.1/scripts/run_phase_c3_3_v0_1.py
.venv/bin/python -m unittest discover -s BioSafe_PhaseC3_3_Retrieval_Oracle_v0.1/tests -p 'test_*.py'
```

This phase produces diagnostics only. It does not authorize C4.