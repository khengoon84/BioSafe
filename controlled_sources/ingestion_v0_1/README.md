# BioSafe controlled ingestion v0.1

This is an **offline additive candidate** for Phase C1/C1.5/C2. It does not modify or connect to the active BioSafe knowledge base, retriever, inference service, or Unified sidecar.

## Current capability

- Loads and validates the controlled staging source register.
- Enforces typed source, page, chunk, warning, and report contracts.
- Recomputes source size and SHA-256 rather than trusting metadata.
- Checks PDF signature, end marker, duplicate hashes, permissions, source eligibility, and extraction-backend availability.
- Writes a deterministic preflight report only when explicitly run with an output path.
- Refuses extraction when there is no configured PDF text backend.
- Validates source-hash-bound component maps and exact within-page boundaries.
- Produces review-gated page/component candidates and citation-page mapping without activating retrieval.
- Produces an extraction-review ledger with explicit reviewed, excluded, fallback-required, OCR-required, and pending dispositions.
- Produces a separate, hash-bound semantic-fallback artifact for reviewed graphical/structural reconstructions without inserting them into component candidates or retrieval.
- Produces additive, source-bound Phase C2 identity-crosswalk and claim-reconciliation artifacts without modifying the active KB, manifest, retrieval, or inference paths.

## Selected extraction backend

`pypdf==6.18.0` is installed in `/home/khengoon/biosafe/.venv` and pinned in the root requirements. It was selected because it is local, pure Python, BSD-3-Clause licensed, supports Python 3.14 and page-aware extraction, and has no mandatory runtime dependencies in this environment.

The extractor preserves page records and warnings; it does not create retrieval chunks. pypdf does not perform OCR and may not reproduce human reading order for complex layouts. Empty/low-text pages, rotated text, unsupported font encodings, and page-extraction errors are retained and flagged for review. PDF catalog labels are stored as `pdf_page_label`; `printed_page_label` remains empty until visually verified against page artwork.

## Act 678 canonical-source decision

The project owner designated the existing staged/local Act 678 file, SHA-256 `8c2badc2db503906b92a42b905736653b868ee3c7bc6fb79719e0081cf25e8cc`, as BioSafe's sole canonical Act 678 corpus source. No text from the previously observed competing publisher PDF may be merged or substituted. This closes source selection only: amendment/currentness, applicability, exact claim support, and live activation remain review-required. All 17 sources may be extracted only into offline artifacts.

## Run deterministic tests

```bash
cd /home/khengoon/biosafe
.venv/bin/python -m unittest discover \
  -s controlled_sources/ingestion_v0_1/tests \
  -p 'test_*.py' -v
```

## Run controlled preflight

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/run_preflight.py \
  --staging-dir controlled_sources/staging_v0_1 \
  --policy controlled_sources/ingestion_v0_1/config/source_policy_v0_1.json \
  --output controlled_sources/ingestion_v0_1/reports/source_preflight_v0_1.json
```

The command is expected to exit with status `2` while source reconciliation and extraction are blocked. That result is not a failed safety control; it is the machine-readable readiness decision.

## Extract selected page records

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/extract_pages.py \
  --staging-dir controlled_sources/staging_v0_1 \
  --policy controlled_sources/ingestion_v0_1/config/source_policy_v0_1.json \
  --document-id KB-WHO-LBM4-RA \
  --output controlled_sources/ingestion_v0_1/reports/risk_assessment_pages_v0_1.json
```

Use `--all-eligible` instead of `--document-id` to extract every policy-eligible source into one offline report.

## Full extraction result — 8 September 2026

`reports/all_sources_pages_v0_1.json` contains page records for all 17 selected sources:

- 1,708 PDF pages and 1,708 page records;
- 1,683 nonempty pages;
- 5,557,192 extracted characters;
- zero page-extraction exceptions;
- 25 empty/possibly decorative pages;
- 80 low-text pages;
- 70 pages with rotated-text/layout warnings;
- 12 pages with CFF encoding warnings that may warrant a `fontTools` evaluation;
- 34 pages with unsupported SymbolSet encoding warnings, all in the scheduled-waste regulations.

`reports/all_sources_extraction_quality_v0_1.json` lists warning counts and exact affected PDF page indexes per document. These artifacts are extraction-complete but not approved for structure-aware chunking or retrieval. Warned pages require targeted visual/semantic review first.

## Build C1.5 component candidates

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/build_components.py \
  --pages controlled_sources/ingestion_v0_1/reports/all_sources_pages_v0_1.json \
  --component-map controlled_sources/ingestion_v0_1/config/component_map_v0_1.json \
  --output controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json \
  --ledger-output controlled_sources/ingestion_v0_1/reports/extraction_review_ledger_v0_1.tsv
```

The current map represents all 17 sources in 61 components and 1,659 candidate chunks. These are page/component-level review candidates, not semantically approved legal-section or form-field chunks. Every candidate has `REVIEW_REQUIRED_BEFORE_CLAIM_USE` and `PROHIBITED_PENDING_PHASE_C_GATES` status.

Important enforced boundaries include:

- `KB-MY-REG2010:PUA367`: PDF pages 1–34 plus only the P.U. (A) 367 portion of page 35; P.U. (A) 368–372 content is excluded.
- `KB-MY-FORME`: User's Guide, Forms A–D, Form E instructions, Form E IBC assessment, Form E applicant Part A, Form F, and closing material are separately scoped and all retained.
- `KB-MY-ACT678`: the selected local hash remains candidate-only with the official-variant/amendment conflict recorded. Page 62 is blank. Rendered page 64 contains publication metadata despite an earlier blank classification, so it is retained as image-only provenance and marked OCR/review-required.
- `KB-MY-SW2005`: operative regulations, seven schedules, and the amendment list are separately scoped. Native text for graphical label pages 18–23 is excluded from candidates pending a reviewed graphical representation.
- Scheduled Wastes SymbolSet review is complete at the extraction-warning level. Source-bound review of all 34 pages confirmed that native layout text retains the visible substantive text and form/table labels on pages 1–17 and 24–34. Pages 18–23 remain graphical-fallback-required. Legal claim, currentness, applicability, and final structure review remain open.
- Empty-page review is complete: 13 source-bound renders are blank and 10 are non-claim publisher/decorative pages; none produces a text candidate.
- Low-volume review is complete at the extraction-warning level. Form bundle page 26 and WHO PPE page 42 contain substantive graphical content and are excluded from native candidates pending reviewed fallback integration. The other 78 rows remain claim- and structure-review-gated.
- Rotated-layout warning review is complete: all 67 formerly pending rows have source-bound visual/text dispositions. Fifty-nine pages retain visible substantive content in native layout text while omitting only redundant rotated template text. Eight pages require reviewed structural fallback and are excluded from native candidates: GMMRA pages 42 and 175 (risk matrices), LBM4 page 43 (control-measure figure), Design pages 55 and 71 (project flowcharts), Outbreak pages 19 and 38 (cyclical framework/workflow), and Programme Management page 56 (dense risk-assessment table with omitted row-group labels and interleaved columns). The ledger has no `REVIEW_PENDING` rows. This closes the extraction-warning review only; accepted pages remain claim- and structure-review-gated, and excluded pages still require semantic fallback integration.
- WHO sources have conservative front-matter, body, references, and annex/back-matter outer boundaries; chapter-level structure and decorative-page review remain pending.

## Targeted fallback evidence

`fonttools==4.64.0` was temporarily installed and benchmarked on all 11 in-scope CFF-warning pages. It removed the warnings but produced zero text-hash or character changes. It was therefore uninstalled and was not added to requirements. The excluded Regulations page 45 is the twelfth CFF-warning page.

`pypdfium2==5.13.0` is pinned as a local CPU-only review renderer and targeted text comparator. It materially recovered rotated text on User's Guide page 26 (74 to 613 characters) and Form E page 211 (274 to 963 characters). Those native pypdf page candidates remain excluded until the fallback text is semantically reviewed and integrated. WHO PPE page 42 is also excluded because its native caption does not represent the illustrated procedure. PDFium did not recover Act page 64 text, and it does not replace the graphical content of Scheduled Wastes labels.

The semantic-fallback artifact currently contains 12 source-bound units. Batch 1A covers the structured table on `KB-WHO-LBM4-PROG` page 56, the 4×4 risk matrix and likelihood key on `KB-MY-GMMRA` page 42, the directed design flow on `KB-WHO-LBM4-DESIGN` page 55, an observation-only five-frame illustrated sequence on `KB-WHO-LBM4-PPE` page 42, and the Third Schedule graphical label set on `KB-MY-SW2005` page 18. Batch 1B adds Scheduled Wastes pages 19–23, the Table 15 matrix and page context on GMMRA page 175, and the operational-maintenance flow and introductory context on WHO Design page 71. Typed validators fail closed on incomplete tables/matrices, invalid graph edges or decision branches, inferred instruction fields in observation-only sequences, incomplete labels, invalid source-context order, incorrect cross-page label numbering, unrecorded graphical/textual conflicts, provenance mismatches, or native-candidate leakage. Every unit remains source-level `HUMAN_REVIEW_REQUIRED`, claim-review-required, activation-prohibited, and deliberately absent from `component_candidates_v0_1.json`.

Build the separate semantic-fallback artifact with:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/build_semantic_fallbacks.py \
  --fallback-map controlled_sources/ingestion_v0_1/config/semantic_fallback_map_v0_1.json \
  --pages controlled_sources/ingestion_v0_1/reports/all_sources_pages_v0_1.json \
  --render-manifest controlled_sources/ingestion_v0_1/reports/targeted_visual_review_v0_1/RENDER_MANIFEST.json \
  --component-artifact controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json \
  --output controlled_sources/ingestion_v0_1/reports/semantic_fallbacks_v0_1.json
```

## Batch 1A independent human-review packet

`config/fallback_human_review_map_v0_1.json` is the editable review record, while `reports/fallback_human_review_packet_v0_1.json` is its deterministic source-bound output. The packet embeds each fallback representation and binds it to the canonical fallback-artifact hash and immutable render provenance. The initial review found four representations `ACCEPT_AS_TRANSCRIBED` and WHO Design page 55 `CORRECTION_REQUIRED`, because both detailed-design branches are visibly labelled `No` but the revision edge was unlabeled. That completed blocked packet is preserved as `reports/fallback_human_review_packet_v0_1_pre_design_correction.json`.

An independent reviewer must compare the listed render with every structured field and complete all source-specific checks. The only permitted dispositions are `ACCEPT_AS_TRANSCRIBED`, `CORRECTION_REQUIRED`, `REJECT_REPRESENTATION`, and `UNRESOLVED_SOURCE_AMBIGUITY`. A completed record requires reviewer identity, role, ISO review date, findings, every check result, and all boundary attestations. `ACCEPT_AS_TRANSCRIBED` means only that the transcription/representation matched the reviewed source. It is not claim approval, a legal/currentness determination, or permission for live activation.

After recording genuine human evidence in the review map, rebuild with:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/build_fallback_human_review_packet.py \
  --review-map controlled_sources/ingestion_v0_1/config/fallback_human_review_map_v0_1.json \
  --fallback-artifact controlled_sources/ingestion_v0_1/reports/semantic_fallbacks_v0_1.json \
  --render-manifest controlled_sources/ingestion_v0_1/reports/targeted_visual_review_v0_1/RENDER_MANIFEST.json \
  --output controlled_sources/ingestion_v0_1/reports/fallback_human_review_packet_v0_1.json
```

If a disposition is `CORRECTION_REQUIRED`, correct the fallback map first, rebuild the fallback artifact, update the review map's source-artifact hash, and restart source comparison for the affected unit. Do not carry an earlier acceptance across changed source-bound bytes.

The Design correction now records both visible `No` branches and validates branch-label multiplicity with a count-aware contract and regression. The corrected fallback artifact is SHA-256 `5235550f7576eb8b0c7892fa3bc1f20e519b54361766a00844cce7f0b7d93dd2`. The four unaffected acceptances were preserved, and the project owner freshly compared and accepted the corrected Design representation. All five units are now `ACCEPT_AS_TRANSCRIBED`, and review-gate status is `TRANSCRIPTION_REVIEW_ACCEPTED_CLAIM_REVIEW_REQUIRED`. This means only that the source transcriptions passed review; claim use and activation remain prohibited.

## Batch 1B transcription review complete

The Batch 1A accepted fallback and packet are preserved for audit as `reports/semantic_fallbacks_v0_1_batch_1a_accepted.json` and `reports/fallback_human_review_packet_v0_1_batch_1a_accepted.json`. Their hashes remain `5235550f7576eb8b0c7892fa3bc1f20e519b54361766a00844cce7f0b7d93dd2` and `93605aa250cca6c3ac940dbca63cd54b3bdf8202fce522b7e173f95d34f4d708`.

The expanded canonical fallback artifact contains 12 units at SHA-256 `9e138862768d28fb1673cce83f3dcd0fb0b34e01b567a2a0f2085e5cc031b347`. Source order shows that `Label 2`, visible at the top of Scheduled Wastes page 19, completes the flammable-liquid entry on page 18; labels 3–11 follow their entries on pages 19–23. The fallback records that cross-page association explicitly. It also keeps adjacent textual symbol specifications separate from rendered-glyph observations. In particular, the page 22 `BAHAN BERJANGKIT` and page 23 `CAMPURAN PELBAGAI BAHAN BERBAHAYA` glyph/text conflicts remain unresolved and must not be treated as legal or currentness determinations.

The BioSafe project owner, acting as source transcription reviewer, compared all seven Batch 1B representations with their immutable renders and accepted each as transcribed. All 12 records are now complete and `ACCEPT_AS_TRANSCRIBED`; the deterministic review packet is SHA-256 `0747d1795a08eacda0d06fc0698ad2992758e99b331b62947e24c80f8052cfb5` with gate `TRANSCRIPTION_REVIEW_ACCEPTED_CLAIM_REVIEW_REQUIRED`. Acceptance confirms source transcription and representation only. It does not resolve the page 22 or 23 glyph/text conflicts, approve any claim, determine legal currentness or applicability, or authorize retrieval or activation. Claim use remains `REVIEW_REQUIRED_BEFORE_CLAIM_USE`; live activation remains `PROHIBITED_PENDING_PHASE_C_GATES`.

## Phase C2 claim-reconciliation foundation

`config/document_identity_crosswalk_v0_1.json` binds all 12 legacy KB document identifiers used by the 45 existing claims to controlled source identifiers and hashes. Eight same-ID mappings are structurally validated. The BioSafe project owner, acting as document identity reviewer on 10 September 2026, compared the controlled identity evidence and accepted four aliases as the same publications under different project identifiers: `KB-MY-DOE2005` → `KB-MY-SW2005`, `KB-MY-MOH2023` → `KB-MY-TRANSPORT2023`, `KB-WHO-PPE` → `KB-WHO-LBM4-PPE`, and `KB-WHO-RA` → `KB-WHO-LBM4-RA`. Each mapping is `HUMAN_IDENTITY_REVIEW_COMPLETE` with source-specific findings. This is identity acceptance only; it does not approve claims or determine amendments, currentness, applicability, compliance, or activation.

`config/claim_reconciliation_map_v0_1.json` preserves all 45 original claim records verbatim and initializes every claim to `REVIEW_REQUIRED_BEFORE_CLAIM_USE`. The all-pending baseline produced by that initialization is preserved byte-identically as `reports/claim_reconciliation_map_v0_1_pre_legal_review.json`. The canonical map currently additionally carries the applied Phase C2 Malaysian legal-claim currentness decision and the completed Form E pilot reviews: nine legal claims are completed with disposition `CURRENTNESS_UNRESOLVED`, four Form E pilot claims are completed (two `INSUFFICIENT_EVIDENCE`, two `SUPPORTED_EXACTLY`), and 32 claims remain pending. Existing `verification_status` values are historical inputs and do not satisfy this gate. A completed supported claim requires atomic propositions, exact source-bound support, authority/jurisdiction, currentness/supersession, allowed decisions/actions, limitations/exclusions, all checks passing, and human review evidence. `INSUFFICIENT_EVIDENCE` may be completed without inventing a support span, but it cannot enter the curated claim set.

The generated `reports/claim_reconciliation_packet_v0_1.json` currently has 45 required reviews, 13 completed reviews — nine `CURRENTNESS_UNRESOLVED` and four Form E pilot reviews (two `INSUFFICIENT_EVIDENCE`, two `SUPPORTED_EXACTLY`) — and two curated claims (CLM-024, CLM-025). Both remain offline, claim-review-required, and `PROHIBITED_PENDING_PHASE_C_GATES`. They are additive artifacts and do not replace or modify `/home/khengoon/biosafe/data/BioSafe_Knowledge_Base_v0.2.json` or `/home/khengoon/biosafe/data/BioSafe_Knowledge_Pack_Manifest_v0.1.json`.

`reports/claim_reconciliation_review_aid_v0_1.json` is a separate navigation-only human-review aid. It retains four completed identity-mapping evidence bundles and contains 45 claim-review items, including controlled metadata, component navigation, conservative legacy-page hints, exact candidate text on hinted pages, accepted fallback representations on hinted excluded pages, currentness/supersession warnings, and domain-specific boundary prompts. It never creates atomic propositions, claim dispositions, claim-reviewer identity, or claim attestations. Identity review is complete with zero mappings pending; 13 claim reviews are complete (nine `CURRENTNESS_UNRESOLVED` and four Form E pilot reviews) and 32 remain pending. The deterministic artifact SHA-256 is `9bf05f8edd507a911a9c90a76f9cfd5b64e5250f38a62891f1882e50b8748d10`.

After the identity-only review, the rebased crosswalk hash is `516788b2aea9978ce7265af7288f2c07e4ef07efa55eb73e4be65548d9e81aae`. The all-pending pre-legal-review map preserved at `reports/claim_reconciliation_map_v0_1_pre_legal_review.json` is `1edf2c9ac74a121f9eeec17f75fe11ddb40bfa7c1daf41c45c62d3d77dffdf5c`, and the canonical map with the applied legal-currentness decision and Form E pilot reviews is `e5e8cd1c56ee8cadbbd33a277b451255a6e6d2a0e74ff4185c4f46012f8410ab`.

The staged Regulations 2010 source repeatedly identifies its target instrument as `P.U. (A) 367`, and the approved component ends before the unique `P.U. (A) 368.` marker. The source-register identifier was corrected from the inconsistent `P.U. (A) 106/2010` to `P.U. (A) 367/2010`; a regression binds the register metadata to the controlled first-page text and existing boundary. This is a metadata correction only. The recorded 2019 schedule-amendment, claim-currentness, applicability, claim-use, and activation gates remain open.

Initialize the review map only when intentionally rebasing it to the exact current source bytes; rebasing resets every claim to pending and discards the applied legal-claim review decision:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/initialize_claim_reconciliation.py \
  --crosswalk controlled_sources/ingestion_v0_1/config/document_identity_crosswalk_v0_1.json \
  --knowledge-base data/BioSafe_Knowledge_Base_v0.2.json \
  --component-artifact controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json \
  --fallback-artifact controlled_sources/ingestion_v0_1/reports/semantic_fallbacks_v0_1.json \
  --fallback-review-packet controlled_sources/ingestion_v0_1/reports/fallback_human_review_packet_v0_1.json \
  --output controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json
```

Build the deterministic offline review packet and curated candidate reference with:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/build_claim_reconciliation.py \
  --crosswalk controlled_sources/ingestion_v0_1/config/document_identity_crosswalk_v0_1.json \
  --review-map controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json \
  --knowledge-base data/BioSafe_Knowledge_Base_v0.2.json \
  --component-artifact controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json \
  --fallback-artifact controlled_sources/ingestion_v0_1/reports/semantic_fallbacks_v0_1.json \
  --fallback-review-packet controlled_sources/ingestion_v0_1/reports/fallback_human_review_packet_v0_1.json \
  --review-packet-output controlled_sources/ingestion_v0_1/reports/claim_reconciliation_packet_v0_1.json \
  --curated-kb-output controlled_sources/ingestion_v0_1/reports/curated_candidate_kb_v0_1.json
```

Build the navigation-only human-review aid with:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/build_claim_review_aid.py \
  --crosswalk controlled_sources/ingestion_v0_1/config/document_identity_crosswalk_v0_1.json \
  --review-map controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json \
  --knowledge-base data/BioSafe_Knowledge_Base_v0.2.json \
  --source-policy controlled_sources/ingestion_v0_1/config/source_policy_v0_1.json \
  --source-register controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv \
  --component-artifact controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json \
  --fallback-artifact controlled_sources/ingestion_v0_1/reports/semantic_fallbacks_v0_1.json \
  --fallback-review-packet controlled_sources/ingestion_v0_1/reports/fallback_human_review_packet_v0_1.json \
  --output controlled_sources/ingestion_v0_1/reports/claim_reconciliation_review_aid_v0_1.json
```

Generate source-coherent, navigation-only markdown briefs for the 36 pending claims with:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/generate_claim_review_briefs.py \
  --review-aid controlled_sources/ingestion_v0_1/reports/claim_reconciliation_review_aid_v0_1.json \
  --review-map controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json \
  --output-dir controlled_sources/ingestion_v0_1/review \
  --generated-date 2026-09-10
```

`review/INDEX.md` links nine briefs grouped by controlled document. The generator verifies
that the review aid is SHA-256-bound to the supplied canonical map and that its pending count
matches the emitted claim set. The briefs copy source-bound navigation suggestions and the
exact reconciliation contract; they do not create dispositions, propositions, reviewer
identity, attestations, regulatory conclusions, or activation decisions. Human decisions
must be recorded in `config/claim_reconciliation_map_v0_1.json` and validated by the existing
claim-reconciliation builder and tests.

Initialize the four-claim Form E pilot worksheet and deliberately incomplete decision packet
with:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/initialize_claim_decision_template.py \
  --review-map controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json \
  --review-aid controlled_sources/ingestion_v0_1/reports/claim_reconciliation_review_aid_v0_1.json \
  --claim-id CLM-018 --claim-id CLM-019 --claim-id CLM-024 --claim-id CLM-025 \
  --batch-id FORME-PILOT-01 \
  --packet-output controlled_sources/ingestion_v0_1/human_review/FORME-PILOT-01/decision_packet.json \
  --worksheet-output controlled_sources/ingestion_v0_1/human_review/FORME-PILOT-01/WORKSHEET.md
```

The initialized packet is `HUMAN_REVIEW_REQUIRED`; all decision fields remain pending,
null, empty, or false. The application CLI refuses it until the human reviewer completes
every decision and explicitly changes the top-level status to `HUMAN_REVIEW_COMPLETE`.
After human completion, validate without writing anything by adding `--dry-run` to:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/apply_claim_review_decisions.py \
  --review-map controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json \
  --decision-packet controlled_sources/ingestion_v0_1/human_review/FORME-PILOT-01/decision_packet.json \
  --crosswalk controlled_sources/ingestion_v0_1/config/document_identity_crosswalk_v0_1.json \
  --knowledge-base data/BioSafe_Knowledge_Base_v0.2.json \
  --components controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json \
  --fallbacks controlled_sources/ingestion_v0_1/reports/semantic_fallbacks_v0_1.json \
  --fallback-reviews controlled_sources/ingestion_v0_1/reports/fallback_human_review_packet_v0_1.json \
  --output controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json \
  --snapshot-output controlled_sources/ingestion_v0_1/reports/claim_reconciliation_map_v0_1_pre_FORME-PILOT-01.json \
  --report-output controlled_sources/ingestion_v0_1/reports/claim_decision_report_FORME-PILOT-01.json \
  --applied-date 2026-09-10 \
  --dry-run
```

Without `--dry-run`, the CLI first validates the existing map and every proposed completed
review using the canonical reconciliation builder, verifies the exact declared changed-claim
set, preserves the prior map bytes in a non-overwritable snapshot, atomically writes the new
map and a hash-bound deterministic report, and refuses reapplication. The map, snapshot, and
report paths must be distinct. No Form E pilot decision has been applied yet.

## Phase C2 Malaysian legal-claim review draft

`config/legal_claim_review_draft_map_v0_1.json` and `reports/legal_claim_review_draft_v0_1.json` provide a separate navigation and atomization aid for the nine existing claims tied to Act 678, the Biosafety (Approval and Notification) Regulations 2010, and the Environmental Quality (Scheduled Wastes) Regulations 2005. The artifact embeds exact controlled candidate text and source hashes, validates locator phrases, carries the controlled currentness/supersession blockers, and proposes editable atomic statements. It cannot update `config/claim_reconciliation_map_v0_1.json`, assign a disposition, provide reviewer identity, or produce attestations.

The draft highlights three material issues for human review: `CLM-006` combines Regulation 17 completeness/resubmission content with terminology that may be confused with the separate Regulation 19 rectification provision; `CLM-007` cannot support a current First Schedule conclusion while `2019_SCHEDULE_AMENDMENT_MUST_BE_RECONCILED`; and `CLM-030` combines source propositions with BioSafe project policy. Scheduled Wastes source text identifies amendment `P.U. (A) 158/2007`, but the controlled policy still records amendment relationships as not fully reconciled. No current-law, exemption, applicability, classification, compliance, or prescribed-pathway conclusion is approved by this draft.

Build the deterministic legal review draft with:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/build_legal_claim_review_draft.py \
  --draft-map controlled_sources/ingestion_v0_1/config/legal_claim_review_draft_map_v0_1.json \
  --review-map controlled_sources/ingestion_v0_1/reports/claim_reconciliation_map_v0_1_pre_legal_review.json \
  --source-policy controlled_sources/ingestion_v0_1/config/source_policy_v0_1.json \
  --component-artifact controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json \
  --output controlled_sources/ingestion_v0_1/reports/legal_claim_review_draft_v0_1.json
```

The current draft map and artifact SHA-256 values are `210e2eb6131d7a98dab8d53ac634b18ba37cb7d7d67e66060d0b1e727fc791af` and `8e7ace043a83c3faea525fe935a6e31e8daa4fd0c1f2019cc293e7040e358e55`. The nine legal-claim reviews have been applied to `config/claim_reconciliation_map_v0_1.json` as completed with disposition `CURRENTNESS_UNRESOLVED` (no support spans; excluded from curation), so the curated candidate KB remains empty; 36 of 45 claim reviews remain pending and live activation remains prohibited.

Apply the recorded human legal-currentness decision to the canonical review map only once; the script refuses claims that are not pending:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/apply_legal_currentness_unresolved_review.py \
  --review-map controlled_sources/ingestion_v0_1/reports/claim_reconciliation_map_v0_1_pre_legal_review.json \
  --legal-draft controlled_sources/ingestion_v0_1/reports/legal_claim_review_draft_v0_1.json \
  --reviewer-identity "BioSafe project owner" \
  --reviewer-role "Claim reconciliation reviewer" \
  --review-date 2026-09-10 \
  --output controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json
```

Generate evidence-only bundles for the three recorded legal blockers with:

```bash
cd /home/khengoon/biosafe
PYTHONPATH=controlled_sources/ingestion_v0_1/src \
  .venv/bin/python controlled_sources/ingestion_v0_1/scripts/generate_legal_blocker_evidence.py \
  --legal-draft controlled_sources/ingestion_v0_1/reports/legal_claim_review_draft_v0_1.json \
  --review-map controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json \
  --components controlled_sources/ingestion_v0_1/reports/component_candidates_v0_1.json \
  --source-policy controlled_sources/ingestion_v0_1/config/source_policy_v0_1.json \
  --source-register controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv \
  --output-dir controlled_sources/ingestion_v0_1/legal_blocker_evidence \
  --generated-date 2026-09-10
```

The generator validates source-policy/component provenance, the source-register hash and
document identities, and the canonical `CLAIM_REVIEW_COMPLETE` /
`CURRENTNESS_UNRESOLVED` / empty-support state for CLM-006, CLM-007, and CLM-030. It also
fails closed if a 2019 amendment record is later added to the controlled source register,
because the current controlled-corpus-gap statement would then require human revision.
The outputs reproduce source-bound passages and component review gates only; they do not
resolve currentness or establish applicability, exemption, approval, notification,
classification, compliance, non-compliance, or a prescribed pathway.

Render selected pages with:

```bash
cd /home/khengoon/biosafe
.venv/bin/python controlled_sources/ingestion_v0_1/scripts/render_review_pages.py \
  --staging-dir controlled_sources/staging_v0_1 \
  --register controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv \
  --selection controlled_sources/ingestion_v0_1/config/targeted_visual_review_pages_v0_1.json \
  --output-dir controlled_sources/ingestion_v0_1/reports/targeted_visual_review_v0_1 \
  --scale 1.5
```

## Boundary

Files under `reports/` and future extracted candidate data are offline review artifacts. They must not be copied into `/home/khengoon/biosafe/data` or referenced by the live pipeline until the Phase C provenance, retrieval, semantic, and human-review gates pass. C1.5 warning disposition is complete with zero `REVIEW_PENDING` rows, but `FALLBACK_REQUIRED...` and `OCR_REQUIRED...` pages remain excluded or non-candidates pending the separate reviewed fallback/OCR workstream. The persistent source-bound review set contains 209 pages, including all 34 Scheduled Wastes pages and all rotated-warning pages.