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

## Verified current-state anchors (10 September 2026)

What does exist and is hash-attested in `controlled_sources/ingestion_v0_1/README.md`:

- Canonical claim map `config/claim_reconciliation_map_v0_1.json` (SHA-256 `a228e643…`):
  45 claims, 9 completed `CURRENTNESS_UNRESOLVED`, 36 pending; all-pending baseline
  preserved byte-identically at `reports/claim_reconciliation_map_v0_1_pre_legal_review.json`
  (`1edf2c9a…`).
- `reports/claim_reconciliation_packet_v0_1.json` (`63c64dda…`): 45 required / 9 completed /
  0 curated, `PROHIBITED_PENDING_PHASE_C_GATES`.
- `reports/curated_candidate_kb_v0_1.json`: intentionally empty (`6d6f70b5…`).
- `reports/claim_reconciliation_review_aid_v0_1.json` (`0cabfdb3…`): navigation aid,
  9 complete / 36 pending.
- All 10 deterministic test suites in `controlled_sources/ingestion_v0_1/tests/` pass
  (run 10 September 2026).

## Open items

1. ~~Owner decision: update `AGENTS.md` to reference `Project_Baseline.md` by its actual
   filename~~ **Applied 10 September 2026**: line 5 of `AGENTS.md` now points to
   `Project_Baseline.md`. The 25-byte `.docx:Zone.Identifier` remnant remains on disk
   (untracked/ignored) pending owner deletion.
2. Per baseline "Changes since baseline v1.0": Unified-3 browser-UI work changed three files
   covered by the Unified-2.2.5.1 promotion hashes → fresh live WSL2/Ollama and human
   validation still required. No live validation has been run in these sessions.
3. Human review of the 36 pending claims and the three legal-claim currentness blockers
   (CLM-006, CLM-007, CLM-030) remains open.
