# BioSafe CRA-7 — Conversational Trajectory Benchmark v0.1

CRA-7 is the first integrated benchmark of the redesigned conversational reasoning architecture.

It evaluates CRA-1 through CRA-6 together through **30 multi-step or cross-component trajectory cases**.

## Families covered
- product help
- clarification
- referential follow-up
- task change
- domain activation
- dependency sufficiency
- semantic verification
- response composition
- state integrity
- reformulation
- document workflow

## Key regression scenarios
The suite explicitly includes the failures that triggered the architecture redesign, but tests them through generalized invariants:

- `who are you?`
- `what kind of document can you review?`
- organism typo clarification followed by `Bacillus anthracis`
- `what approval did you mean?`
- `why?`
- generic biosafety without Form E/transport/waste leakage
- species identity without LMO inference
- explicit transport/waste/Form E domain activation
- unresolved LMO prerequisites
- inferred LMO status rejected as a prerequisite
- risk/containment context dependencies
- unknown-to-fact hallucination blocking
- wrong-jurisdiction evidence blocking
- compliance/certification blocking
- clean product-help rendering
- correction conflict becoming `disputed`
- reformulation bypassing RAG
- document workflow recognition

## Important scope
CRA-7 is still a **controlled architecture benchmark**. It does not yet connect the new CRA stack to the live Flask/browser product.

That deliberate separation lets us verify conversational reasoning before changing the working application.

## Install
```bash
cd /home/khengoon/biosafe/BioSafe_CRA7_Conversational_Trajectory_Benchmark_v0.1
python scripts/install_cra7_v0_1.py
```

## Run
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/run_cra7_trajectory_benchmark_v0_1.py
```

The run creates:
`/home/khengoon/biosafe/cra_v1/reports/cra7_trajectory_report_v0_1.json`

Please provide that JSON after the run so it can be reviewed directly before we move to integration.
