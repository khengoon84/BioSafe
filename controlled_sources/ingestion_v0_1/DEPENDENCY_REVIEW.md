# PDF extraction dependency review

**Decision date:** 8 September 2026  
**Selected package:** `pypdf==6.18.0`  
**Install target:** `/home/khengoon/biosafe/.venv` only

## Decision

`pypdf` is the preferred first-line extractor for BioSafe's controlled authoritative-source collection.

| Criterion | pypdf 6.18.0 | Assessment |
|---|---|---|
| Execution | Local, pure Python | Meets local-only/data-protection boundary |
| License | BSD-3-Clause | Permissive for this repository |
| Python | Requires Python >=3.9; PyPI classifies Python 3.14 | Compatible with active Python 3.14.4 environment |
| Runtime dependencies | None required on Python 3.14 for base install | Small dependency and memory footprint |
| Page handling | Page-by-page extraction and PDF catalog page labels | Supports provenance-oriented page records |
| OCR | Not provided | Image-only pages must be flagged; OCR remains a separate governed decision |
| Layout | Layout mode available but rotated/complex text can be incomplete | Capture warnings and require quality review |

For the five rotated-text pages observed in the WHO Risk Assessment probe, layout mode retained 103–1,448 more characters per page than plain mode. Layout mode remains the default and the affected pages are marked `ROTATED_TEXT_OMITTED_BY_LAYOUT_MODE`; no lossy automatic fallback is applied.

## Alternatives considered

- **PyMuPDF:** fast and capable, but distributed under AGPL-3.0 or a commercial license. It was not selected for the default BioSafe path because of the materially different licensing obligation.
- **pdfplumber:** useful for detailed table/layout work and permissively licensed, but brings `pdfminer.six`, Pillow, and `pypdfium2`. It may be evaluated later as a targeted fallback if benchmarked documents demonstrate extraction failures that pypdf cannot address.
- **OCR tools/services:** not selected. They introduce a separate accuracy, provenance, resource, privacy, and security problem. No external document service is authorized.

## Installed-package evidence

- Version: `6.18.0`
- License expression: `BSD-3-Clause`
- Install location: `/home/khengoon/biosafe/.venv/lib/python3.14/site-packages`
- `pip check`: no broken requirements
- Root requirement: `pypdf==6.18.0`

## Use boundary

pypdf output is an untrusted extraction artifact, not an authoritative claim. Every page remains linked to the immutable source hash. Empty, low-text, rotated-text, unsupported-font-encoding, and parser-error pages are retained and warned. PDF catalog labels and visually verified printed labels are separate fields. Extraction does not activate documents, construct legal claims, or connect output to live retrieval.

For encrypted PDFs, the adapter attempts only the standard empty password. A successful empty-password open is recorded as `PDF_DECRYPTED_WITH_EMPTY_PASSWORD`. Any PDF requiring a non-empty password remains `BLOCKED_ENCRYPTED`; the adapter does not guess or bypass passwords.