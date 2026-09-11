# Human claim-review worksheet — KB-WHO-LBM4-PPE-REVIEW-01

Version: `BioSafe_Claim_Review_Pilot_Worksheet_v0.1`.

**Status: HUMAN REVIEW COMPLETE. Human comparison confirmed by the BioSafe project owner on 2026-09-11.**

Canonical map SHA-256: `bc52b44020503b0887c192fedeefd747265fe1931601b68fe1d54c36c1753c08`.
Review aid SHA-256: `6431166758a6e8d5805f0f839394fef0e57fd51091da10156d4d242c2969a01c`.

For each claim, compare the immutable staged PDF with the cited candidate text. Do not treat a navigation suggestion as support. Record the completed human decision in the JSON template; then set top-level `human_review_status` to `HUMAN_REVIEW_COMPLETE` only after every field, check, and attestation is complete.

## CLM-042

Original claim: WHO places PPE within broader laboratory biosafety core requirements rather than treating PPE as a complete safety determination. Core requirements include good microbiological practice and procedure, with PPE such as laboratory coats, footwear, gloves and eye protection used as applicable.

Controlled document: `KB-WHO-LBM4-PPE`
Controlled source SHA-256: `016a46c280a7d0801c69fa5f44bfa350b8217f1a1eff608ac26678d97129cf55`
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

## CLM-043

Original claim: WHO indicates that some PPE needs are determined by risk assessment; for example, respiratory protection for biological agents is not a general core requirement and becomes a heightened control measure when the risk assessment indicates it is needed.

Controlled document: `KB-WHO-LBM4-PPE`
Controlled source SHA-256: `016a46c280a7d0801c69fa5f44bfa350b8217f1a1eff608ac26678d97129cf55`
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
| CLM-042 | 1. Core requirements are foundational/integral combined risk-control measures.<br>2. GMPP is the most important laboratory-facility requirement and a code of practice for activities with biological agents.<br>3. PPE core requirements list laboratory coats, footwear, gloves, and eye protection. | 29 | Do not attribute categorical “complete safety determination” wording to WHO. |
| CLM-043 | 1. Respiratory protection is not generally a biological-agent core requirement; risk-assessment indication makes it a heightened control.<br>2. Risk assessment may determine additional PPE and local assessment guides control selection.<br>3. Respiratory protection only protects wearer; other measures may be needed for others/environment.<br>4. Selection follows risk assessment and trained use. | 29, 33, 35 | No project-specific PPE/respirator determination; do not use excluded graphical PDF 42. |

## Human PDF comparison record

Controlled PDF: `/home/khengoon/biosafe/controlled_sources/staging_v0_1/KB-WHO-LBM4-PPE_Personal_Protective_Equipment.pdf`
SHA-256: `016a46c280a7d0801c69fa5f44bfa350b8217f1a1eff608ac26678d97129cf55`

Compare JSON quotes and surrounding context on PDF 29 (printed 13), PDF 33 (printed 17), and PDF 35 (printed 19). PDF 42 is excluded from native candidates and is not used.

- [x] Visually confirm every quote and surrounding context.
- [x] Confirm every proposition is direct and atomic.
- [x] Preserve the PPE-as-not-a-complete-safety-determination phrase as a boundary, not attributed WHO wording.
- [x] Do not use excluded graphical PDF 42.
- [x] Preserve international-guidance, wearer-only, and domain-separation boundaries.
- [x] Do not make project-specific PPE, respiratory-protection, safety, approval, containment, or regulatory determinations.
- [x] Record final disposition, reviewer identity/role/date, checks, and attestations in `decision_packet.json`.
- [x] Set top-level status complete only after every claim is complete.

## Completed human review record

Reviewer: `BioSafe project owner`
Role: `Claim reconciliation reviewer`
Review date: `2026-09-11`
Outcome: CLM-042 and CLM-043 are `SUPPORTED_AFTER_ATOMIC_SPLIT`. PDF page 42 was not used. The categorical PPE-as-not-a-complete-safety-determination wording remains a BioSafe boundary, not attributed WHO source evidence. Claim use remains separately gated and live activation remains prohibited.
