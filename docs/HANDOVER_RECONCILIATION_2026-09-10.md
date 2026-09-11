# Handover / Workspace Reconciliation Note (10 September 2026)

Scope: verify artifacts referenced during the 10 September 2026 session against the actual
workspace at commit `b3799bd` (post `Zone.Identifier` cleanup). This note records exact
findings so future sessions do not rely on unverified session summaries.

## Referenced artifacts that do not exist

An exhaustive filesystem search (excluding `.venv/` and `.git/`) and a full git-history
search (both commits, all filters) found **no trace — never created, never committed** — of:

| Referenced artifact | Search outcome |
|---------------------|----------------|
| `controlled_sources/ingestion_v0_1/config/claim_reconciliation_status.json` | Absent (disk + history) |
| `controlled_sources/ingestion_v0_1/config/all_sources_phase_status.json` | Absent (disk + history) |
| `controlled_sources/ingestion_v0_1/config/pipeline_status.json` | Absent (disk + history) |
| `controlled_sources/ingestion_v0_1/config/material_compliance_status.json` | Absent (disk + history) |
| `controlled_sources/ingestion_v0_1/scripts/run_phases_pre_flight.py` | Absent (disk + history) |
| Stage-QC report (`*stage_qc*`) | Absent |
| Config-completeness report (`*config_completeness*`) | Absent |

No file matching `*status*.json` exists anywhere in the repository. The only preflight assets
are per-module preflight scripts (each module directory carries its own), plus
`controlled_sources/ingestion_v0_1/scripts/run_preflight.py` with its output
`reports/source_preflight_v0_1.json` and the top-level `src/preflight_check.py`.

## Source of the phantom references

- The in-repo baseline (`Project_Baseline.md`, whose H1 is "BioSafe Project Handover and
  Technical Baseline"), `README.md`, and `docs/ARCHITECTURE_FREEZE.md` make **no** reference
  to any of the artifacts above (verified by grep).
- The references originated in a **compacted session summary**, not from any in-repo
  document. Conclusion: the discrepancy was between that session summary and the workspace —
  not between the in-repo baseline and the workspace. The in-repo baseline is therefore
  usable as an evidence source on this point.

## AGENTS.md filename mismatch

`AGENTS.md` directs agents to read
`BioSafe_Project_Handover_and_Technical_Baseline_v1.0.md`. That filename does not exist.
The matching in-repo document by content is `Project_Baseline.md` (same H1 title). The only
remnant of the referenced filename is
`BioSafe_Project_Handover_and_Technical_Baseline_v1.0.docx:Zone.Identifier` — an NTFS
alternate-data-stream artifact (25 bytes) whose base `.docx` was never committed. AGENTS.md
should be updated to point to `Project_Baseline.md` (owner decision).

## Verified current-state anchors (updated 11 September 2026)

What does exist and is hash-attested in `controlled_sources/ingestion_v0_1/README.md`:

- Canonical claim map `config/claim_reconciliation_map_v0_1.json` (SHA-256 `47fc793a…`):
  45 claims, 44 completed (9 `CURRENTNESS_UNRESOLVED` + 8 Form E + 4 contained-use
  + 3 Malaysian GMM risk-assessment guidance + 3 Malaysian transport guidance + 3 IBC governance
  + 9 WHO LBM4 risk-assessment guidance + 3 WHO LBM4 core-manual claims + 2 WHO LBM4 PPE claims), 1 pending;
  all-pending baseline preserved byte-identically at `reports/claim_reconciliation_map_v0_1_pre_legal_review.json`
  (`1edf2c9a…`).
- `reports/claim_reconciliation_packet_v0_1.json` (`9e73fa98…`): 45 required / 44 completed /
  31 curated, `PROHIBITED_PENDING_PHASE_C_GATES`.
- `reports/curated_candidate_kb_v0_1.json` (`535973aa…`): 31 offline curated candidate claims.
- `reports/claim_reconciliation_review_aid_v0_1.json` (`4c080490…`): navigation aid,
  44 complete / 1 pending in 1 controlled document.
- All deterministic test suites in `controlled_sources/ingestion_v0_1/tests/` pass
  after the WHO LBM4 PPE review application (run 11 September 2026).

## Open items

1. ~~Owner decision: update `AGENTS.md` to reference `Project_Baseline.md` by its actual
   filename~~ **Applied 10 September 2026**: line 5 of `AGENTS.md` now points to
   `Project_Baseline.md`. The orphaned `.docx:Zone.Identifier` remnant and the other orphaned
   ADS metadata files were subsequently deleted; all remaining ADS metadata is ignored.
2. **Live revalidation attempted 10 September 2026 and failed.** Compilation and the current
   deterministic semantic-gate suite passed (22/22), but the inspected live suite passed
   36/37 and human review found additional unsupported permit/regulatory claims. See
   `docs/UNIFIED2251_LIVE_REVALIDATION_2026-09-10.md`. Unified-2.2.5.1 remains an unpromoted
   candidate; defect remediation requires a separate approved plan.
3. A navigation-only brief for the remaining pending claim now exists under
   `controlled_sources/ingestion_v0_1/review/`; human review remains open.
4. Evidence-only bundles for CLM-006, CLM-007, and CLM-030 now exist under
   `controlled_sources/ingestion_v0_1/legal_blocker_evidence/`. The 2019 First/Third Schedule
   amending instrument is not in the controlled source register, so CLM-007 remains blocked.
