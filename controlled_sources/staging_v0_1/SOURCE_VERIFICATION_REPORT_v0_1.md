# BioSafe source verification report v0.1

**Verification date:** 8 September 2026  
**Scope:** Phase C0 verification of the eight original local candidates  
**Activation effect:** None — all sources remain disconnected from live RAG

## Results

| Source | Official comparison | Current-listing evidence | Remaining limitation |
|---|---|---|---|
| KB-MY-ACT678 | The local file is byte-identical to a still-live official endpoint; a different publisher PDF was also observed | Project owner designated the local hash as BioSafe's sole canonical Act 678 source on 9 September 2026 | Source selection is closed; amendment/currentness, applicability, claim support, and live activation review remain required |
| KB-MY-REG2010 | Byte-identical to current official endpoint | Listed by the current homepage | The separately listed 2019 First/Third Schedule amendment must be reconciled |
| KB-MY-GMMRA | Byte-identical to current official endpoint | Listed by the current homepage | Scope remains GMM/LMO-specific; no superseding guideline established in this pass |
| KB-MY-CU | Byte-identical to current official endpoint | Listed by the current homepage | Scope remains LMO contained use; no superseding guideline established in this pass |
| KB-MY-IBC | Byte-identical to current official endpoint | Listed by the current homepage | IBC governance is not a researcher-facing approval determination |
| KB-MY-FORME | Byte-identical to current official endpoint | Listed by the current homepage | Procedural/current operational reconciliation remains required; Form E is not an approval or permit |
| KB-WHO-LBM4 | Byte-identical to WHO IRIS English bitstream for handle `10665/337956` | WHO publication page identifies the fourth edition | Claim-level extraction and review pending |
| KB-WHO-BIOSEC | Byte-identical to WHO IRIS English bitstream for handle `10665/377754` | WHO publication page identifies the 2024 guidance | Claim-level extraction and review pending |

## WHO page-count reconciliation

The staged WHO Laboratory Biosecurity Guidance is not a different file from the official source. Its SHA-256 and size match the official IRIS English bitstream exactly. WHO's publication page reports **110 pages**, while the IRIS bibliographic description reports **xvii, 88 p.** These are different page-count conventions for the same PDF and must be retained as separate metadata fields during extraction (PDF page index versus printed page label/front matter).

The WHO LBM4 core shows the same type of convention difference: the publication page reports **124 pages**, while IRIS describes **xvii, 101 p.** The file is byte-identical to the official IRIS English bitstream.

## Verification method

For each source, the official endpoint response was required to be a structurally valid PDF. Size and SHA-256 were compared with the staged file. Official-page listing evidence was inspected separately from byte equivalence. No publisher file was substituted into staging.

### Act 678 canonical-source decision

- Staged file and still-live official KB endpoint (`/assets/document/akta-dan-peraturan/1-akta-biokeselamatan-2007-akta-678.pdf`): 1,174,486 bytes; SHA-256 `8c2badc2db503906b92a42b905736653b868ee3c7bc6fb79719e0081cf25e8cc`.
- Current homepage-linked official file (`/assets/document/Akta%20678.pdf`): 1,014,927 bytes; SHA-256 `196ac44261e3e18e357f055ba232f3b1cee6dbc01b501918678032e2e3fb779c`.

Both endpoints returned structurally valid PDFs from `biosafety.gov.my`. This verification pass did not establish whether the difference is only presentation/OCR or includes substantive text. On 9 September 2026, the project owner designated the existing local/staged file (SHA-256 `8c2badc2db503906b92a42b905736653b868ee3c7bc6fb79719e0081cf25e8cc`) as BioSafe's sole canonical Act 678 source. No content from the competing PDF may be merged or substituted. This closes the BioSafe source-selection question but does not establish that the canonical file incorporates every amendment, is current for every claim, applies to a particular case, or supports a legal conclusion. Those gates remain separate.

## Boundary

Byte equivalence and current listing establish identity and publisher provenance only where the listed file matches. They do not establish that every provision is unamended, that a source applies to a particular case, or that a specific extracted statement supports a consequential claim. The Act 678 corpus source is now fixed by owner decision; amendment/currentness and claim adequacy remain review-required. Live activation remains prohibited pending the remaining Phase C gates.
