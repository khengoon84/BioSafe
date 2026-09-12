# BioSafe Phase C3.1 — Retrieval Gate Closure v0.1

This is an additive closure benchmark for Phase C3. It does not alter the committed
C3 v0.1 package, the live KB, the frozen retrievers/routers, or any model/runtime.
It tests a crosswalk-aware candidate adapter against the reviewed 32-claim corpus.

The report is descriptive and gate-enforcing: the hard-gate result is recorded, but
no candidate is promoted and no C4 sidecar is created. C4 remains blocked until the
owner reviews this report and explicitly approves the next phase.

Run:

```bash
cd /home/khengoon/biosafe
.venv/bin/python BioSafe_PhaseC3_1_Retrieval_Gate_v0.1/scripts/run_phase_c3_1_v0_1.py
.venv/bin/python -m unittest discover -s BioSafe_PhaseC3_1_Retrieval_Gate_v0.1/tests -p 'test_*.py'
```

The candidate adapter maps only retrieval eligibility through the human-reviewed
document identity crosswalk. Returned evidence retains controlled document IDs.
Claim use remains `REVIEW_REQUIRED_BEFORE_CLAIM_USE`, and activation remains
`PROHIBITED_PENDING_PHASE_C_GATES`.