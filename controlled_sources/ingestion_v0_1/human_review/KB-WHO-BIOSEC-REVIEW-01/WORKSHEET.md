# Human claim-review worksheet — KB-WHO-BIOSEC-REVIEW-01

Version: `BioSafe_Claim_Review_Pilot_Worksheet_v0.1`.

**Status: HUMAN REVIEW COMPLETE. Human comparison confirmed by the BioSafe project owner on 2026-09-11.**

Canonical map SHA-256: `47fc793a8f8fa4d5f05c8dcb8ac14793bb23b563a81eceffe18901f9ef099b42`.
Review aid SHA-256: `4c08049098a7c3f1f4d0f4b65ca2e5d8607f36b7931f63ba624454eec78092aa`.

For each claim, compare the immutable staged PDF with the cited candidate text. Do not treat a navigation suggestion as support. Record the completed human decision in the JSON template; then set top-level `human_review_status` to `HUMAN_REVIEW_COMPLETE` only after every field, check, and attestation is complete.

## CLM-034

Original claim: WHO's 2024 laboratory biosecurity guidance applies a risk- and evidence-based approach to biosecurity, including governance, secure handling, transport/storage and high-consequence research risk management.

Controlled document: `KB-WHO-BIOSEC`
Controlled source SHA-256: `0be0952e29286d6d527d557cca8ef1b20d7cf3d299adf3cd008611bd01f32b2f`
Candidate navigation IDs: none
Accepted fallback navigation IDs: none

Required boundary prompts:
- A navigation suggestion is not claim support or a review disposition.
- Unknown, conflicting, or currentness-unresolved information must remain unresolved.
- WHO material is international guidance, not Malaysian law or regulatory proof.

Reviewer checklist:
- [x] Compared immutable staged PDF and source-bound candidate text
- [x] Atomized the claim without adding unsupported meaning
- [x] Recorded exact quote/page/source IDs for every supported proposition
- [x] Recorded authority, jurisdiction, currentness, and supersession
- [x] Recorded allowed decisions/actions, limitations, and exclusions
- [x] Recorded reviewer identity, role, ISO date, and findings
- [x] Set all required checks to `PASS` and attestations to `true`
- [x] Confirmed every claim-specific boundary prompt above was preserved

## Draft proposition-to-passage matrix

**Draft only:** These are navigation and atomization aids, not a disposition or completed human findings. Reviewer-controlled JSON fields remain incomplete.

| Claim | Proposed propositions | PDF pages | Material review issue |
|---|---|---|---|
| CLM-034 | 1. The 2024 revision applies a risk- and evidence-based approach to laboratory biosecurity.<br>2. The approach is applied to high-consequence research and other activities involving biosecurity-relevant material, technology, and/or information.<br>3. Tools and best practices cover laboratory, institution, and national-regulatory levels and lifecycle examples including collection, transport, processing, storage, and possible destruction.<br>4. A two-tier IBC/national-regulatory-body system is described for review and oversight of high-consequence work. | 21, 23 | Narrow “governance” to stated structures; do not attribute “secure handling” to these passages or infer Malaysian requirements. |

## Human PDF comparison record

Controlled PDF: `/home/khengoon/biosafe/controlled_sources/staging_v0_1/KB-WHO-BIOSEC_Laboratory_Biosecurity_Guidance.pdf`
SHA-256: `0be0952e29286d6d527d557cca8ef1b20d7cf3d299adf3cd008611bd01f32b2f`

Compare JSON quotes and surrounding context on PDF 21 (printed 1) and PDF 23 (printed 3).

- [x] Visually confirm every quote and surrounding context.
- [x] Confirm every proposition is direct and atomic.
- [x] Narrow governance to the source’s stated levels, tools, committee function, and two-tier model.
- [x] Do not attribute the historical phrase “secure handling” to the cited passages.
- [x] Preserve international-guidance, institutional-review/regulator, and domain-separation boundaries.
- [x] Do not make project-specific high-consequence, governance, handling, transport, storage, control, approval, compliance, or regulatory determinations.
- [x] Record final disposition, reviewer identity/role/date, checks, and attestations in `decision_packet.json`.
- [x] Set top-level status complete only after the claim is complete.

## Completed human review record

Reviewer: `BioSafe project owner`
Role: `Claim reconciliation reviewer`
Review date: `2026-09-11`
Outcome: CLM-034 is `SUPPORTED_AFTER_ATOMIC_SPLIT`. Governance remains narrowed to the source’s stated levels, tools, committee function, and two-tier model; “secure handling” is not attributed to the cited passages. Claim use remains separately gated and live activation remains prohibited.
