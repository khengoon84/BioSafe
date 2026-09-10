# Controlled authoritative source staging v0.1

This directory contains candidate authoritative source files preserved for provenance review. It includes files copied unchanged from the user's existing local collection and files downloaded unchanged from verified publisher-controlled websites.

## Status

- **Staging only:** files in this directory are not yet approved as authoritative BioSafe evidence.
- **Disconnected:** this directory is not connected to the live BioSafe knowledge base, retriever, or inference path.
- **Per-source status:** consult `SOURCE_REGISTER.tsv`. Seven of the eight original local candidates are byte-identical to their current official publisher-linked files. The project owner has designated the staged/local Act 678 file (SHA-256 `8c2badc2db503906b92a42b905736653b868ee3c7bc6fb79719e0081cf25e8cc`) as BioSafe's sole canonical Act 678 source; the previously observed competing publisher PDF is historical provenance only and must not be merged or substituted. The nine acquired files came directly from official publisher endpoints. Currentness, amendment/supersession relationships, applicability, legal effect, and claim-level suitability still require the per-source review recorded in the register and verification report.
- **Originals preserved:** source files were copied or downloaded as published; PDF contents were not modified.

`SOURCE_REGISTER.tsv` records source identity and provenance, normalized staged filename, size, SHA-256 digest, verification status, and inclusion rationale. `SHA256SUMS.txt` supports later integrity checks.

`SOURCE_VERIFICATION_REPORT_v0_1.md` records the 8 September 2026 official-equivalence checks and the WHO page-count reconciliation. None of these verification updates activates a source for live retrieval.

## Official acquisition batch — 2026-09-08 UTC

The following were downloaded from official publisher-controlled endpoints:

- seven WHO *Laboratory Biosafety Manual, 4th edition* subject-specific monographs, using WHO publication pages and WHO IRIS repository records;
- Ministry of Health Malaysia's *Guidelines For The Safe Transport Of Clinical Specimens And Infectious Substances In Malaysia 2023*;
- Malaysia Department of Environment's *Environmental Quality (Scheduled Wastes) Regulations 2005 — P.U. (A) 294/2005*.

Download provenance does not by itself establish that a document is current, unsuperseded, applicable to a particular case, or adequate to support a specific claim.

Do not derive regulatory conclusions from these files until source verification and claim-to-source review are complete.
