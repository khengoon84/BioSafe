# Extraction review notes v0.1

**Run date:** 8 September 2026  
**Parser:** `pypdf==6.18.0`  
**Activation:** Prohibited pending Phase C gates

## Completion

- Documents requested: 17
- Documents represented: 17
- PDF pages: 1,708
- Page records: 1,708
- Nonempty pages: 1,683
- Extracted characters: 5,557,192
- Page-extraction exceptions: 0

## Structured warnings

| Warning | Page count | Required disposition |
|---|---:|---|
| `PAGE_TEXT_EMPTY_POSSIBLE_SCAN_OR_DECORATIVE_PAGE` | 25 | Visually determine whether each page is decorative/blank or requires OCR/fallback. |
| `PAGE_TEXT_LOW_VOLUME_REVIEW_REQUIRED` | 80 | Check divider, cover, page-number-only, or unexpectedly missing content. |
| `ROTATED_TEXT_OMITTED_BY_LAYOUT_MODE` | 70 | Compare affected tables/side labels with page artwork before chunking. |
| `FONT_ENCODING_CFF_REQUIRES_FONTTOOLS` | 12 | Evaluate targeted `fontTools` support only if visual comparison shows missing or corrupt text. |
| `FONT_ENCODING_SYMBOLSET_UNSUPPORTED` | 34 | Review every affected scheduled-waste page; symbols or glyphs may be incomplete. |

The exact pages are listed by document in `all_sources_extraction_quality_v0_1.json`.

## Encryption handling

`KB-MY-REG2010` and `KB-MY-SW2005` are encrypted PDFs that accept the standard empty password. They were extracted and marked `PDF_DECRYPTED_WITH_EMPTY_PASSWORD`. The adapter does not guess or bypass non-empty passwords.

## Act 678 owner selection

The project owner initially selected the existing local/staged Act 678 file for offline extraction and, on 9 September 2026, designated that file (SHA-256 `8c2badc2db503906b92a42b905736653b868ee3c7bc6fb79719e0081cf25e8cc`) as BioSafe's sole canonical Act 678 corpus source. No content from the previously observed competing publisher PDF may be merged or substituted. This closes source selection but does not establish amendment consolidation, currentness for a claim, applicability, claim support, or live eligibility.

## Semantic spot checks

Expected title/legal-identifier signals were found in all 17 extracted document texts. Beginning/middle/end samples were also inspected across the collection and were recognizable as the expected sources. This establishes basic extraction identity, not completeness or claim-level correctness.

## Next gate

Do not construct or activate retrieval chunks yet. First review warned pages and decide whether any source/page requires a targeted parser fallback or OCR. Then design document-type-specific structure segmentation and claim-to-span review.

## C1.5 component-boundary progress — 8 September 2026

- All 17 source documents are represented in the machine-readable component map.
- `KB-MY-REG2010` is fail-closed at the unique `P.U. (A) 368.` marker on PDF page 35. Pages 36–45 and the P.U. (A) 368 portion of page 35 cannot become candidates.
- All User's Guide and Forms A–F material is retained. Form E is further divided into instructions/preliminary details (pages 202–207), IBC assessment (208–209), and applicant Part A (210–215), with mutually exclusive researcher/IBC domains.
- Act 678 PDF page 62 was rendered and confirmed blank. PDF page 64 was previously owner-classified blank, but source-bound rendering visibly shows Royal Assent and Gazette publication metadata. Page 64 is therefore retained in provenance and marked `OCR_REQUIRED_OWNER_CLASSIFICATION_CONFLICT`; no extracted claim has been created from it.
- Scheduled Wastes is divided into operative regulations, Schedules 1–7, and the amendment list. SW 404 on PDF page 13 visibly matches the native extraction. This confirms the text match only; applicability and claim-level interpretation remain later gates.
- Scheduled Wastes PDF pages 18–23 visibly contain essential hazard-label graphics. Native text alone is not an adequate representation of those graphics, and those pages are excluded from candidate chunks pending fallback review.
- Conservative outer components were mapped for all nine WHO sources. Fine chapter/annex structure and decorative-page dispositions remain open.

### Fallback benchmarks

- `fonttools==4.64.0` was temporarily installed and tested on the 11 in-scope CFF-warning pages. CFF warnings fell from 11 to zero, but no text hash and no character count changed. The package was uninstalled and not retained.
- `pypdfium2==5.13.0` was installed and pinned for local rendering and targeted text comparison. It materially recovered rotated text on User's Guide page 26 and Form E page 211. The native candidates for those pages remain excluded pending semantic review of the fallback text.
- PDFium did not recover Act page 64 text. No OCR engine is currently installed, so that page remains an explicit OCR/review blocker.

### Current gate status

The component artifact is still offline and review-gated. It is not an accepted live corpus. Remaining pending warning dispositions, fine structure, printed-page verification, fallback integration, claim reconciliation, retrieval tests, live WSL2/Ollama tests, and human semantic review must be completed before promotion.

## C1.5 warning-review continuation — 9 September 2026

- All 23 previously pending empty-text warnings were source-bound rendered. Thirteen pages were confirmed visually blank. Ten pages were solid-colour endpapers or publisher back-cover artwork without technical or regulatory claim content. Their immutable page records remain in provenance and none generates a text candidate.
- All 80 low-volume pages were source-bound rendered and compared with pypdf plain-mode and PDFium text extraction plus image-content metrics. Covers, dividers, all high-density outliers, and representative running-matter pages received direct visual inspection. Seventy-eight warnings contain only visibly represented source-title/divider text, decorative artwork, or running matter; this closes the extraction-volume warning only and does not approve claims or fine structure.
- Form bundle page 26 contains a substantive rotated biotechnology diagram, and WHO PPE page 42 contains an illustrated disposable-apron removal sequence. Native text is not an adequate representation of either page. Both are explicitly fallback-required and excluded from native candidates; this newly removes PPE page 42 from the candidate set.
- All 67 still-pending rotated-layout pages were source-bound rendered. Targeted review of the largest extraction deltas confirms that the common WHO template trigger is the vertical `SECTION` label while substantive prose remains native-extracted. The pages have not all received complete figure/table semantic review, so none of these 67 pending rows was bulk-accepted.
- All 34 Scheduled Wastes pages were source-bound rendered and individually inspected. Native layout extraction retains visible substantive text and form/table labels on pages 1–17 and 24–34; their SymbolSet warnings are accepted at extraction-warning level only. Pages 18–23 contain essential hazard pictograms and remain graphical-fallback-required and excluded from native candidates. Legal claim, currentness, applicability, and final structure review remain open.
- At this pre-rotated-review snapshot, the ledger had 67 `REVIEW_PENDING` rows, all rotated-layout warnings, and the output had 61 components and 1,667 activation-prohibited candidate chunks. The later section below supersedes these counts.
- Continuation validation passed 47/47 deterministic ingestion tests. Two consecutive component rebuilds were byte-identical at SHA-256 `f7b44aa9475220c3ddb4f2c48d489a40cbe196b1f0c52aee16c07e2850d29794` for the unchanged candidate artifact and `dd9422c9e873cb00afb471da434d615f7b4da46caf92ba116491d117f2626a2f` for the updated ledger. The persistent review selection and render manifest now cover 209 pages; all 209 PNGs were checked against their manifest hashes, and the 15 renders in the previously stale persistent manifest were byte-identical to their replacements.
- The repository still has no Git metadata. The prior 8 September temporary protected-file snapshot is not present in this resumed session, so its 22-file comparison was not rerun. The legacy environment integrity manifest confirms unchanged hashes for the active knowledge-pack manifest and safety gate but predates later pipeline changes; current live pipeline inspection confirms it still references only the original active KB and manifest and does not reference candidate reports.

## C1.5 rotated-layout page review — 9 September 2026

- All 67 previously pending rotated-layout rows were compared against native layout text and available source-bound renders page by page. Reliable direct visual evidence supported 49 dispositions. Forty-two pages were accepted at extraction-warning level because visible headings, body prose, lists, boxes, or table cell text remain in native layout extraction and the omitted rotated content is redundant section-template or cover-spine text. This does not approve claims, table semantics, currentness, applicability, or final structure.
- Seven pages visibly contain substantive two-dimensional or path semantics that native page text does not represent authoritatively: `KB-MY-GMMRA` pages 42 and 175 (likelihood-by-consequence matrices), `KB-WHO-LBM4` page 43 (likelihood/consequence control-measure figure), `KB-WHO-LBM4-DESIGN` pages 55 and 71 (project flowcharts), and `KB-WHO-LBM4-OUTBREAK` pages 19 and 38 (cyclical risk-assessment framework and specimen workflow). Their immutable page records remain in provenance, but their seven native page candidates are excluded pending reviewed fallback integration.
- At this intermediate review point, 18 rows remained explicitly `REVIEW_PENDING`: `KB-WHO-LBM4` pages 85, 97, 103, and 111; `KB-WHO-LBM4-PPE` pages 73, 75, and 81; `KB-WHO-LBM4-PROG` pages 17, 19, 21, 23, 27, and 56; and `KB-WHO-LBM4-RA` pages 15, 19, 27, 28, and 39. Temporary scale-reduced PNGs and focused crops were generated from the hash-verified local sources, but the image transport remained unreliable. No visual disposition was inferred from extractor text alone. The final section below supersedes this state.
- Pre-exclusion impact analysis found exactly one existing page candidate for each of the seven fallback pages, totalling 17,562 extracted characters. The resulting offline artifact has 61 components and 1,660 activation-prohibited candidate chunks; the ledger retains 231 rows with 18 pending.
- Three new exact-partition/provenance/visual-coverage regression tests were added. The deterministic suite passes 50/50. Two consecutive canonical rebuilds were byte-identical: candidate SHA-256 `0b5cf0b674444c746be96a0009993f8eb35983840e241fe0e64210addc44407f`; ledger SHA-256 `98f9cf80e33b1b8661fc6541b1232cf2257ba34ab00d8ff55f582be926b3b133`. All 209 persistent PNG hashes match `RENDER_MANIFEST.json`, `pip check` reports no broken requirements, and runtime-isolation inspection still finds no candidate/staging references outside the controlled-source area and baseline documentation.
- The active KB and active knowledge-pack manifest were not modified; their observed SHA-256 values remain `3d68f8154f6952a33395b253925ee44c2842a046c3c11d55f8c12ee9eb386bb4` and `199145afd64b1fb41f38921aba90ac214193f199dda4eb29f649c10eadf11031` respectively. Live WSL2/Ollama tests were not applicable to this offline configuration/report change and were not run.

## C1.5 final rotated-layout dispositions — 9 September 2026

- The 18 remaining immutable PNG renders were transported successfully and compared individually with their native layout extraction. Seventeen pages are accepted at extraction-warning level: `KB-WHO-LBM4` pages 85, 97, 103, and 111; `KB-WHO-LBM4-PPE` pages 73, 75, and 81; `KB-WHO-LBM4-PROG` pages 17, 19, 21, 23, and 27; and `KB-WHO-LBM4-RA` pages 15, 19, 27, 28, and 39. Visible prose, headings, lists, table/matrix values, or figure labels needed to understand these pages remain in native extraction. Omitted rotated `SECTION` text is redundant; on RA page 28 the omitted vertical `Risk` title is redundant to the retained caption and risk endpoints. These dispositions do not approve claims or final structure.
- `KB-WHO-LBM4-PROG` page 56 is fallback-required. Its dense biosecurity risk-assessment table has material two-dimensional structure: native extraction omits the rotated `Description` and `Examples` row-group labels and interleaves examples across columns. The immutable page record remains in provenance, but its one native candidate (8,215 characters) is excluded pending reviewed semantic fallback integration.
- The completed rotated-warning partition is 59 `ACCEPT_NATIVE_TEXT_ROTATED_TEMPLATE_LABEL_NONMATERIAL`, eight `FALLBACK_REQUIRED_SUBSTANTIVE_ROTATED_STRUCTURE`, two pre-existing `FALLBACK_REQUIRED_SUBSTANTIVE_ROTATED_CONTENT`, and one pre-existing `ACCEPT_PROSE_ROTATED_SECTION_LABEL_NONMATERIAL`. No ledger row remains `REVIEW_PENDING`.
- The eighth structural exclusion brings the rotated-review exclusion impact to eight page candidates and 25,777 native-extracted characters. At warning-disposition completion, the offline artifact had 61 components and 1,659 activation-prohibited candidate chunks (SHA-256 `a865db80e4459f31e1dc8e17ea98af35b1a32a54173309c15a7be827854c8527`). The ledger retained 231 rows with zero pending (SHA-256 `1cee16fbe04e4d6e1687ca05c1e66603ef80d419e6b44780ebbc69dea79216eb`). The later owner-decision metadata rebuild supersedes only the component-artifact hash, as recorded below.
- Two canonical temporary rebuilds were byte-identical. The deterministic suite passes 50/50, all 209 persistent render hashes match the manifest, and dependency/runtime-isolation checks pass. The active KB and active knowledge-pack manifest remain unchanged at the hashes recorded above. Live WSL2/Ollama tests are not applicable to this offline map/artifact change and were not run.
- Phase C1.5 warning disposition is complete. This does not promote the candidate corpus or complete the separate fallback/OCR, fine-structure, printed-page-label, claim reconciliation, retrieval, live-model, or human semantic-review gates.

## Phase C2 claim-reconciliation foundation — 10 September 2026

- An additive document-identity crosswalk covers all 12 legacy document IDs referenced by the existing 45 claims. Four differing-ID source mappings remain explicitly human-review-required; no title match is treated as accepted identity evidence.
- The source-bound claim-reconciliation map preserves all 45 claims and initializes every record as review-required. The generated review packet has zero completed reviews, and the activation-prohibited curated candidate KB intentionally contains zero claims.
- Supported dispositions require exact native-candidate or reviewed-fallback references and complete human evidence. Unsupported claims may be dispositioned without invented support, but cannot enter the curated set. Historical `verification_status` labels are not claim approval.
- Each atomic proposition in a supported claim requires direct exact support, and fallback support is accepted only when the exact fallback unit has a completed `ACCEPT_AS_TRANSCRIBED` review record. The focused C2 suite passes 15/15 and the full deterministic ingestion suite passes 87/87; compilation and dependency checks pass. Independent builds byte-match canonical at `18e11a12de8fd660e1bc8b056532716e8784c1a84aa8bae6490ab9377af2d160` for the review packet and `6c4aaefadd6c8a42ea50fb94c8610961eec9bdf0ddce1fc8d9b584e6f9df05fe` for the empty curated candidate artifact. Live WSL2/Ollama tests were not run because no runtime path changed.
- Checkpoint 1 preparation adds a navigation-only review aid with four identity bundles and 45 claim items. Twenty-two claims have conservative page hints, 23 require manual navigation, and 16 remain blocked by four pending identity aliases. The aid makes no review decision and is deterministic at `ca46e3e550ddf1e06d670c5e8db927ddb91cccdfea30f1164f6a11cc4c0ae8af`. The Regulations 2010 register identifier was corrected to `P.U. (A) 367/2010` after the controlled source and existing exact boundary demonstrated P.U. (A) 367 ending before P.U. (A) 368; amendment/currentness review remains open. Focused aid and reconciliation suites pass 11/11 and 15/15, and the full deterministic suite passes 98/98. No human identity or claim review is represented as complete.
- The BioSafe project owner subsequently completed document-identity review and accepted all four differing-ID mappings as the same publications under different project identifiers. Source-specific findings preserve that this is identity acceptance only. The rebased map propagates completed identity status while retaining all 45 claims as review-required; the curated artifact remains empty. The current crosswalk, map, claim packet, curated artifact, and navigation aid hashes are `516788b2aea9978ce7265af7288f2c07e4ef07efa55eb73e4be65548d9e81aae`, `1edf2c9ac74a121f9eeec17f75fe11ddb40bfa7c1daf41c45c62d3d77dffdf5c`, `fc5340b9a7e77d8d28d61c783ae9f06a0b366faaf1f16734850b5920c3f524b7`, `6d6f70b54d36b158381aa3a17f8cdb3bce17826d7fd25019fac304b25bfa827d`, and `d6c918a171a49c8e8cb8bd593d462dc12435382013884f66adf1c7a9c9975184`. Independent builds byte-match canonical. Amendment, currentness, applicability, and claim support remain unresolved where recorded.
- Checkpoint 2 preparation adds a nine-record Malaysian legal-claim draft aid, source-bound to controlled candidates and source-policy currentness blockers. It records no disposition or human claim review. Material flags cover the `CLM-006` Regulation 17/19 terminology boundary, the `CLM-007` unreconciled 2019 schedule amendment, the `CLM-030` source/project-policy mixture, and the rule that biological waste is not automatically SW 404. The draft map and artifact hashes are `210e2eb6131d7a98dab8d53ac634b18ba37cb7d7d67e66060d0b1e727fc791af` and `8e7ace043a83c3faea525fe935a6e31e8daa4fd0c1f2019cc293e7040e358e55`. Focused tests pass 8/8 and the full deterministic suite passes 106/106; independent builds byte-match canonical. All legal claim decisions remain pending.

## C1 semantic-fallback pilot — 9 September 2026

- A separate typed semantic-fallback contract and deterministic builder were added. Fallback units must match immutable page and render provenance, retain explicit limitations, contain complete structured-table cells, require claim review, and prohibit live activation.
- `KB-WHO-LBM4-PROG` PDF page 56 is the first pilot. Its source-bound reconstruction preserves the visible four-stage process, seven columns, and distinct rotated `Description` and `Examples` row groups. The native page remains in provenance and excluded from component candidates.
- This pilot is a transcription/reconstruction artifact, not a C2-approved claim or retrieval chunk. Its cell semantics require human source comparison before later integration, and the remaining fallback/OCR pages are still pending.
- The owner-decision metadata rebuild retains 61 components, 1,659 candidates, and 231 ledger rows. Its component artifact SHA-256 is `7e1bfcde1ddbdfd07039147ebe25ef787ad3ce1dca1eefcab58149585756422c`; the unchanged ledger remains `1cee16fbe04e4d6e1687ca05c1e66603ef80d419e6b44780ebbc69dea79216eb`; and the hardened one-unit fallback artifact is `e454940f88eeb5dba930f3abdf1c5d5cd7e3b455c2b82d5dc9504dce0cacf6f4`.

## C1 Batch 1A typed semantic-fallback pilots — 9 September 2026

- The fallback contract now has representation-specific fail-closed validation for `structured_table`, `risk_matrix`, `directed_flow`, `illustrated_sequence`, and `graphical_label_set`. Review state is separated into source-bound transcription, source-bound semantic comparison, and mandatory human review; no AI-assisted record is represented as human-approved.
- `KB-MY-GMMRA` page 42 preserves the complete 4×4 likelihood/consequence matrix, likelihood definitions, and the source qualifiers that the matrix is not definitive and that uncertainty and assumptions must be considered. It cannot by itself assign containment or determine acceptability.
- `KB-WHO-LBM4-DESIGN` page 55 preserves the design-flow nodes, visible `Yes`/`No` branches, revision loops, procurement-route bypass, construction terminal, and stop terminal. The source-visible detailed-design revision line has no visible branch label and remains explicitly unlabeled rather than inferred.
- `KB-WHO-LBM4-PPE` page 42 preserves five source-visible frames as observations only. The source has no textual step labels; no imperative procedural instructions were invented.
- `KB-MY-SW2005` page 18 preserves Third Schedule/Regulation 10 context and two visible graphical label specifications. Only the explosive-waste entry visibly carries `Label 1`; no second printed label number was invented. Applicability, SW 404 classification, amendments, and claim-level currentness remain separate gates.
- All five fallback units remain in component provenance, absent from native candidates, `HUMAN_REVIEW_REQUIRED`, claim-review-required, activation-prohibited, and disconnected from runtime retrieval. Thirteen other unique fallback/OCR pages remain unrepresented after this pilot batch.
- The focused semantic-fallback suite passes 10/10 and the full deterministic ingestion suite passes 61/61. Two independently generated five-unit fallback artifacts were byte-identical; the canonical SHA-256 is `d494bcc170cc76439d89c788c5df8d3bfb7a42b57464434f3695d152376f8802`. Independent integrity checks confirmed 61 components, 1,659 candidates, 231 ledger rows, zero pending, five provenance-only fallback pages, and 209/209 render hashes. `pip check` reports no broken requirements. The component artifact and ledger remain unchanged at `7e1bfcde1ddbdfd07039147ebe25ef787ad3ce1dca1eefcab58149585756422c` and `1cee16fbe04e4d6e1687ca05c1e66603ef80d419e6b44780ebbc69dea79216eb`.

## C1 Batch 1A human-review gate packet — 9 September 2026

- A separate typed human-review map, validator, builder, and deterministic packet now bind all five fallback units to fallback artifact `d494bcc170cc76439d89c788c5df8d3bfb7a42b57464434f3695d152376f8802` and their immutable source/render provenance. The packet contains 26 source-specific checks across the five units.
- The packet deliberately records five required reviews and zero completed reviews. Every disposition, reviewer identity/role/date, and check result is null; findings are empty and boundary attestations are false. Independent human source comparison remains the blocker.
- Completed records fail closed unless they use an allowed disposition, contain reviewer evidence and an ISO date, cover every required check, include findings, and affirm that review is not claim approval or live activation. Disposition/check-result consistency is enforced. Even a complete `ACCEPT_AS_TRANSCRIBED` record remains claim-review-required and activation-prohibited.
- Two generated packets were byte-identical and matched the canonical report. The pending review-packet SHA-256 is `25f572db2f9b2c02f97dff97fdcdc212a8204b63ec8f81d6f7d77f0084355a76`. The new focused suite passes 7/7. No human review outcome is asserted.

### Human review 1 of 5 — WHO Programme page 56

- The BioSafe project owner, acting as source transcription reviewer, confirmed on 9 September 2026 that they compared immutable render `KB-WHO-LBM4-PROG_page_056.png` (SHA-256 `3b92b204753b3dd702449b21808126f9c15879ec5329fba386921726033ea7d4`) with the structured representation.
- The reviewer selected `ACCEPT_AS_TRANSCRIBED` and recorded `PASS` for the table title, four-stage/seven-column order, distinct `Description` and `Examples` row groups, cell associations, and limitations. The reviewer affirmed that this transcription review is neither claim approval nor live activation.
- The review packet now records one completed review and four pending reviews and remains overall `HUMAN_REVIEW_REQUIRED`, claim-review-required, and activation-prohibited. Two rebuilt packets were byte-identical; the superseding packet SHA-256 is `bbce8c82d619d1d6b5f352f011a914a428eb35225aa11f65d6e96776fb3ec513`.

### Human reviews 2–5 — Batch 1A source comparison complete, correction required

- The same reviewer compared the immutable GMMRA page 42, WHO Design page 55, WHO PPE page 42, and Scheduled Wastes page 18 renders with their source-bound representations. GMMRA, PPE, and Scheduled Wastes were `ACCEPT_AS_TRANSCRIBED`, with every source-specific check passing and the claim/activation boundaries affirmed.
- WHO Design page 55 was dispositioned `CORRECTION_REQUIRED`. The source visibly labels both outgoing paths from `Approve detailed design` to `Revise detailed design` and to `Unacceptable outcome` as `No`; the current representation leaves the revision edge label empty. `approval_branches` and `revision_loops` failed, while node text/types, edge geometry, bypass/terminals, and excluded-inference checks passed.
- All five review records are complete, comprising four `ACCEPT_AS_TRANSCRIBED` and one `CORRECTION_REQUIRED`. Completion does not imply passage: the aggregate `review_gate_status` is `BLOCKED_CORRECTION_REQUIRED`. Claim use remains `REVIEW_REQUIRED_BEFORE_CLAIM_USE`, live activation remains `PROHIBITED_PENDING_PHASE_C_GATES`, and the Design representation must be corrected and re-reviewed against new artifact bytes before Batch 1A can clear its transcription gate.
- The completed blocked review packet SHA-256 is `d58a77244eb28d970b2e470b4d68945e0f9e333964e030c5f188eb16901cb0cf`.
- Final post-review validation passes 8/8 focused human-review tests and 69/69 full deterministic ingestion tests. Two final packet builds and the canonical packet are byte-identical at `d58a77244eb28d970b2e470b4d68945e0f9e333964e030c5f188eb16901cb0cf`; all 209 render hashes verify, `pip check` is clean, and runtime isolation remains intact.

### WHO Design correction applied — fresh review pending

- The completed blocked packet was preserved as `fallback_human_review_packet_v0_1_pre_design_correction.json` at SHA-256 `d58a77244eb28d970b2e470b4d68945e0f9e333964e030c5f188eb16901cb0cf` before changing source-bound bytes.
- Directed-flow validation now compares branch-label multisets rather than sets. The detailed-design decision declares `Yes`, `No`, `No`, and both source-visible `No` edges—to revision and unacceptable outcome—are transcribed. A regression removes one duplicate `No` and confirms fail-closed rejection.
- Two corrected five-unit fallback builds were byte-identical. The corrected fallback artifact SHA-256 is `5235550f7576eb8b0c7892fa3bc1f20e519b54361766a00844cce7f0b7d93dd2`.
- The review map is rebound to the corrected artifact. Four unaffected `ACCEPT_AS_TRANSCRIBED` reviews remain; Design alone was reset with null reviewer data/results and false attestations. Two current review-packet builds were byte-identical at `584904f1106139540970d1d10e7964fbdeeed7c9aa9b16b35b9b8e89d7e1733e`. Current status is four of five complete and `BLOCKED_HUMAN_REVIEW_REQUIRED` pending fresh Design comparison. Claim use and activation remain prohibited.

### Fresh Design review accepted — Batch 1A transcription gate complete

- The BioSafe project owner freshly compared the corrected Design representation against immutable render `KB-WHO-LBM4-DESIGN_page_055.png`. All six Design checks passed, including both visible `No` branches from `Approve detailed design`; disposition is `ACCEPT_AS_TRANSCRIBED`.
- All five Batch 1A representations are now accepted as transcribed. The packet reports `HUMAN_REVIEW_COMPLETE` and `TRANSCRIPTION_REVIEW_ACCEPTED_CLAIM_REVIEW_REQUIRED`. This closes only the transcription/representation review gate. Claim use remains `REVIEW_REQUIRED_BEFORE_CLAIM_USE`, live activation remains `PROHIBITED_PENDING_PHASE_C_GATES`, and no legal/currentness, applicability, compliance, containment, or approval conclusion follows.
- Two final review-packet builds were byte-identical at SHA-256 `93605aa250cca6c3ac940dbca63cd54b3bdf8202fce522b7e173f95d34f4d708`.

## C1 Batch 1B fallback construction — 9 September 2026 — INDEPENDENT REVIEW PENDING

- Seven source-page fallback units were added: Scheduled Wastes pages 19–23, GMMRA page 175, and WHO Design page 71. The canonical artifact now contains 12 units. All remain absent from native candidates, claim-review-required, activation-prohibited, and disconnected from runtime retrieval.
- Source-order comparison corrected the preliminary continuation assumption. The printed label marker follows its entry: `Label 2` at the top of page 19 completes the flammable-liquid entry on page 18, while labels 3–11 follow their entries on pages 19–23. A typed cross-page assignment records the single page 18→19 relationship and rejects non-adjacent targets, missing targets, marker/number mismatch, pre-numbered targets, and document-level number collisions.
- Enhanced graphical-label records keep the adjacent textual symbol specification separate from the visible rendered-glyph observation. Page 22 `BAHAN BERJANGKIT` specifies a three-crescent symbol in text but presents a flame-over-circle-like glyph in the source-bound render. Page 23 `CAMPURAN PELBAGAI BAHAN BERBAHAYA` specifies `Simbol (nil)` and a striped background but also presents a flame-over-circle-like glyph. Both are explicitly `CONFLICT`; neither side is adjudicated as legally authoritative. Page 23 also preserves the first three visible numbered label requirements and the four-row colour/reference table. Requirements 4–8 remain native-text provenance on page 24 and are outside this page-23 fallback unit.
- GMMRA page 175 preserves the complete 4×4 Table 15 matrix and ordered page context. Its likelihood-definition key is explicitly `ABSENT_FROM_SOURCE_PAGE`; definitions were not borrowed from page 42. WHO Design page 71 preserves its introductory prose, three parallel maintenance-option paths, convergence, downstream training/SOP/monitoring/assessment sequence, and continual-improvement terminal without inventing decision labels or route preference.
- The accepted Batch 1A artifacts were preserved as `semantic_fallbacks_v0_1_batch_1a_accepted.json` (`5235550f7576eb8b0c7892fa3bc1f20e519b54361766a00844cce7f0b7d93dd2`) and `fallback_human_review_packet_v0_1_batch_1a_accepted.json` (`93605aa250cca6c3ac940dbca63cd54b3bdf8202fce522b7e173f95d34f4d708`). The pre-design-correction blocked packet remains unchanged.
- Two 12-unit fallback builds were byte-identical at SHA-256 `9e138862768d28fb1673cce83f3dcd0fb0b34e01b567a2a0f2085e5cc031b347`. Two review-packet builds were byte-identical at SHA-256 `ec36989599563a233fd4aba3af49394d171d17bd2c2fb5cd4d7206f4baa44e2f`.
- The review packet retains the five completed Batch 1A acceptances and adds seven empty Batch 1B records. Current status is five of 12 complete, seven pending, `HUMAN_REVIEW_REQUIRED`, and `BLOCKED_HUMAN_REVIEW_REQUIRED`. Acceptance of a faithful conflict transcription would not resolve the underlying symbol conflict or approve claim use.
- Focused suites pass 13/13 semantic-fallback tests and 8/8 human-review tests; the full deterministic ingestion suite passes 72/72. All 209 render hashes verify, `pip check` is clean, runtime isolation passes, and hygiene invariants pass. Component candidates and the ledger remain unchanged at `7e1bfcde1ddbdfd07039147ebe25ef787ad3ce1dca1eefcab58149585756422c` and `1cee16fbe04e4d6e1687ca05c1e66603ef80d419e6b44780ebbc69dea79216eb`. Active KB and manifest remain unchanged at `3d68f8154f6952a33395b253925ee44c2842a046c3c11d55f8c12ee9eb386bb4` and `199145afd64b1fb41f38921aba90ac214193f199dda4eb29f649c10eadf11031`.
- Live WSL2/Ollama testing was not run because Batch 1B is an offline fallback/review-artifact change and does not touch retrieval, inference, model configuration, or activation. Independent source comparison remains the next required action.

## C1 Batch 1B transcription review complete — 9 September 2026

- The BioSafe project owner, acting as source transcription reviewer, compared all seven Batch 1B structured representations with their immutable renders and completed every source-specific check. Scheduled Wastes page 19 was also compared with page 18 for the cross-page `Label 2` association. All seven records are `HUMAN_REVIEW_COMPLETE` and `ACCEPT_AS_TRANSCRIBED`, with all checks passing and all claim-approval and live-activation boundary attestations acknowledged.
- Acceptance of pages 22 and 23 confirms that the structured records faithfully preserve the visible glyphs, adjacent textual specifications, and explicit `CONFLICT` status. It does not adjudicate either representation as legally authoritative. GMMRA page 175 acceptance confirms that no likelihood-definition key appears on that source page and none was borrowed. No acceptance determines waste applicability, SW 404 classification, containment, activity acceptability, legal currentness, compliance, approval, facility fitness, or hazard-specific suitability.
- Two 12-unit fallback builds were byte-identical and matched the unchanged canonical SHA-256 `9e138862768d28fb1673cce83f3dcd0fb0b34e01b567a2a0f2085e5cc031b347`. Two completed review-packet builds were byte-identical at SHA-256 `0747d1795a08eacda0d06fc0698ad2992758e99b331b62947e24c80f8052cfb5`. The packet now reports 12 of 12 complete, `HUMAN_REVIEW_COMPLETE`, and `TRANSCRIPTION_REVIEW_ACCEPTED_CLAIM_REVIEW_REQUIRED`.
- Focused suites pass 13/13 semantic-fallback tests and 8/8 human-review tests; the full deterministic ingestion suite passes 72/72. Compilation completed, all 209 render hashes verify, `pip check` reports no broken requirements, and runtime-isolation and hygiene checks pass. Component candidates and the ledger remain unchanged at `7e1bfcde1ddbdfd07039147ebe25ef787ad3ce1dca1eefcab58149585756422c` and `1cee16fbe04e4d6e1687ca05c1e66603ef80d419e6b44780ebbc69dea79216eb`. Active KB and manifest remain unchanged at `3d68f8154f6952a33395b253925ee44c2842a046c3c11d55f8c12ee9eb386bb4` and `199145afd64b1fb41f38921aba90ac214193f199dda4eb29f649c10eadf11031`.
- Claim use remains `REVIEW_REQUIRED_BEFORE_CLAIM_USE`; live activation remains `PROHIBITED_PENDING_PHASE_C_GATES`. Retrieval integration, active knowledge artifacts, inference, and model configuration were not changed. Live WSL2/Ollama tests were not run because this remains an offline review-record and report change.