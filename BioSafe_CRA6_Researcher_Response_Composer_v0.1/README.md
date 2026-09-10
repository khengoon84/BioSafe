# BioSafe CRA-6 — Researcher Response Composer v0.1

CRA-6 converts **verified structured decisions** into clean researcher-facing responses.

## Response types
- `product_help`
- `simple_answer`
- `educational_answer`
- `needs_clarification`
- `regulatory_assessment`
- `document_review`
- `form_e_assist`
- `safety_redirect`

## User-facing hierarchy
Sections are conditional, not mandatory:

1. Direct answer
2. Why this matters — only when useful
3. What I need from you — only when clarification is necessary
4. What to do next — only when there is a useful action
5. Sources & evidence — collapsed

## Generalized safeguards
- Failed semantic verification cannot be rendered.
- Product-help answers do not expose regulatory evidence.
- Safety redirects do not expose unnecessary regulatory evidence.
- Missing information becomes explicit clarification questions.
- Clarification questions are not duplicated under next steps.
- Educational explanations are kept separate from source references.
- Empty headings are not rendered.
- Developer/internal metadata is not part of the ordinary response object.
- The same rigid regulatory template is not forced onto every answer.

## Important
CRA-6 is still isolated from the live browser UI.
It prepares the response structure that the future integration layer will render.

## Install
```bash
cd /home/khengoon/biosafe/BioSafe_CRA6_Researcher_Response_Composer_v0.1
python scripts/install_cra6_v0_1.py
```

## Test
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra6_response_composer_v0_1.py
```
