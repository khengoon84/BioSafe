# BioSafe Phase C3.2 — Retrieval Diagnostics v0.1

C3.2 corrects the C3.1 benchmark oracle and adds failure attribution. It is an
offline, additive diagnostic package. C3 and C3.1 remain unchanged; the live KB,
pipeline, retrievers, routers, models, and activation state are unchanged.

It evaluates the base frozen retrievers, the actual frozen integration router,
and a crosswalk-aware diagnostic candidate. The candidate uses the reviewed
document identity crosswalk dynamically for eligibility only; returned evidence
keeps controlled IDs. It is not a C4 integration and does not authorize live use.

Run:

```bash
cd /home/khengoon/biosafe
.venv/bin/python BioSafe_PhaseC3_2_Retrieval_Diagnostics_v0.1/scripts/run_phase_c3_2_v0_1.py
.venv/bin/python -m unittest discover -s BioSafe_PhaseC3_2_Retrieval_Diagnostics_v0.1/tests -p 'test_*.py'
```

The benchmark contains 32 canonical cases, 32 distinct claim-specific
paraphrases, and seven boundary controls. Boundary judgments check both claim
IDs and document IDs. Results are descriptive and gate review remains required.