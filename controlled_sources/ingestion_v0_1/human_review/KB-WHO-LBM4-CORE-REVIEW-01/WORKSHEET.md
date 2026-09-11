# Human claim-review worksheet — KB-WHO-LBM4-CORE-REVIEW-01

Version: `BioSafe_Claim_Review_Pilot_Worksheet_v0.1`.

**Status: HUMAN REVIEW COMPLETE. Human comparison confirmed by the BioSafe project owner on 2026-09-11.**

Canonical map SHA-256: `e5787962d750f8a66964416a9ec422900f3714c733933a44c8f155bed82a9b07`.
Review aid SHA-256: `1d0feb7f9b50869e17077bf38550f71f029fd3af2b26d72ce2dc7639c14cdb02`.

For each claim, compare the immutable staged PDF with the cited candidate text. Do not treat a navigation suggestion as support. Record the completed human decision in the JSON template; then set top-level `human_review_status` to `HUMAN_REVIEW_COMPLETE` only after every field, check, and attestation is complete.

## CLM-031

Original claim: WHO LBM4 uses an evidence- and risk-based approach in which safety measures are balanced against the actual risk of the activity on a case-by-case basis.

Controlled document: `KB-WHO-LBM4`
Controlled source SHA-256: `dc0dfd4e65a0dc87410aa73280fe12bfe412df3affd97bd27dc8a4e733379fba`
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

## CLM-035

Original claim: WHO LBM4 includes dedicated guidance on decontamination and waste management; BioSafe should use it as authoritative international corroboration where Malaysian requirements do not fully specify technical practice.

Controlled document: `KB-WHO-LBM4`
Controlled source SHA-256: `dc0dfd4e65a0dc87410aa73280fe12bfe412df3affd97bd27dc8a4e733379fba`
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

## CLM-041

Original claim: WHO LBM4 uses an evidence- and risk-based approach so that safety measures are balanced against the actual risk of work with biological agents on a case-by-case basis; a proper risk assessment should be performed before activities and should inform risk control measures.

Controlled document: `KB-WHO-LBM4`
Controlled source SHA-256: `dc0dfd4e65a0dc87410aa73280fe12bfe412df3affd97bd27dc8a4e733379fba`
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

**Draft only:** These are navigation and atomization aids, not dispositions or completed human findings. Reviewer-controlled JSON fields remain incomplete.

| Claim | Proposed propositions | PDF pages | Material review issue |
|---|---|---|---|
| CLM-031 | 1. LBM4 adopts a risk- and evidence-based rather than prescriptive biosafety approach.<br>2. A thorough, evidence-based and transparent risk assessment allows safety measures to be balanced with actual risk case-by-case. | 19, 22 | Framework principle only; no project-specific risk/control/safety inference. |
| CLM-035 | The core manual lists decontamination and waste management among associated monographs for more detailed information. | 23 | Exclude BioSafe product policy and do not borrow detailed support from the separate DECON monograph. |
| CLM-041 | 1. Thorough, evidence-based and transparent assessment balances measures with actual risk case-by-case.<br>2. The manual states facilities handling biological agents have an obligation to assess work and select/apply appropriate controls.<br>3. Assessment gathers/evaluates information to inform and justify implementation of risk controls. | 19, 26 | Remove unsupported “proper” qualifier; framework does not authorize a specific activity. |

## Human PDF comparison record

Controlled PDF: `/home/khengoon/biosafe/controlled_sources/staging_v0_1/KB-WHO-LBM4_Laboratory_Biosafety_Manual_4th_Edition.pdf`
SHA-256: `dc0dfd4e65a0dc87410aa73280fe12bfe412df3affd97bd27dc8a4e733379fba`

Compare JSON quotes and surrounding context on PDF 19 (printed preliminary matter), PDF 22 (printed 2), PDF 23 (printed 3), and PDF 26 (printed 6).

- [x] Visually confirm every quote and surrounding context.
- [x] Confirm every proposition is direct and atomic.
- [x] Exclude historical BioSafe product-policy wording from CLM-035 source evidence.
- [x] Do not borrow detailed content from KB-WHO-LBM4-DECON for CLM-035.
- [x] Preserve international-guidance, risk-group/containment, and domain-separation boundaries.
- [x] Do not make project-specific risk, control, safety, approval, containment, waste-classification, transport, or regulatory determinations.
- [x] Record final disposition, reviewer identity/role/date, checks, and attestations in `decision_packet.json`.
- [x] Set top-level status complete only after every claim is complete.

## Completed human review record

Reviewer: `BioSafe project owner`
Role: `Claim reconciliation reviewer`
Review date: `2026-09-11`
Outcome: CLM-031 and CLM-041 are `SUPPORTED_AFTER_ATOMIC_SPLIT`. CLM-035 is `PARTIALLY_SUPPORTED`: the associated-monograph proposition is supported, while the historical BioSafe product-policy clause remains excluded and is not WHO source evidence. CLM-035 is not eligible for offline curation. Claim use remains separately gated and live activation remains prohibited.
