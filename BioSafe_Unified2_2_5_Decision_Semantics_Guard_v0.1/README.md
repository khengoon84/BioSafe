# BioSafe Unified-2.2.5 — Decision Semantics, Prerequisite & Answer-Coverage Guard v0.1

Experimental port: **8776**. Existing 8775 and all frozen components remain unchanged.

## Invariants
1. Unknown != No.
2. Regulatory conclusions require prerequisite facts.
3. No positive or negative legal/compliance verdicts.
4. Exact legal citations require exact evidence provenance.
5. Multi-subject definition questions must address every requested subject or explicitly state insufficiency.
6. Sensitive refusals must use a safety rationale, not "query incomplete".

## Install
```bash
python scripts/install_unified225_v0_1.py
```

## Contract
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/unified_v1/tests/test_unified225_contract_v0_1.py
```
Expected: **6/6 PASS**

## Start 8776
```bash
cd /home/khengoon/biosafe
source .venv/bin/activate
PYTHONPATH=/home/khengoon/biosafe/unified_v1/src python /home/khengoon/biosafe/cra_v1/scripts/run_unified225_sidecar_v0_1.py
```

## A/B
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_ab_unified225_v0_1.py
```

## Strengthened semantic acceptance
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_semantic_acceptance_v0_1.py
```

Human wording, applicability and provenance review remains mandatory before freeze.

## Contract change (frozen-layer correction, 2026-09-12)

`DecisionSemanticsGuard` in `unified_v1/src/biosafe_unified225/guards.py` now
requires scoped evidence to support an authorization claim (subject + normative
force) even when keyword prerequisites are present; keyword prerequisites gate
which facts are still needed and never authorize a determination. Previously, a
cited positive claim was silently removed by the citation rule without
populating `missing_information`, and a prereq-keyword query could keep a
positive claim with zero evidence. The contract harness was converted to a real
unittest (8 cases) with regressions for both defects. The 2251 successor guard
already implements these semantics and was not modified. 2251/C5 suites and
CRA3–CRA8 regression suites were re-run to confirm no fallout.

## Live validation result (2026-09-12, honest status)

Live A/B hard assertions: **28/32 PASS** against the corrected module
(pre-change run with the stale pre-correction module: 29/32; the corrected
deterministic contract is 8/8). The 4 live failures are pre-existing and not
introduced by this correction:

- `insufficient_present` (permit_unknown): the model/retrieval sentence
  "You need a Biosafety Permit (BP) for the described activity." still passes
  the guard because 225's `POS` patterns do not classify "you need a ... permit"
  as an authorization claim. Closing this requires extending the frozen `POS`
  pattern list — a further approved frozen-layer change, not done here.
- `pi_expanded` / `ibc_expanded`: model-output-dependent subject expansion;
  the coverage guard correctly fail-closed ("not enough scoped evidence to
  expand ... confidently") when the model output lacked the spelled-out
  expansion this run.
- `safety_reason`: the model gave an "ambiguous query" rationale instead of an
  "incomplete" one, so `SafetyRationaleGuard`'s trigger condition did not match.

Sidecars were stopped after validation; no live service left running.
