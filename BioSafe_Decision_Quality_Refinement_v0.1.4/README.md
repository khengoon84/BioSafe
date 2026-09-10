# BioSafe Decision Quality Refinement v0.1.4

Final narrow Stage 9 decision-flow refinement after real app testing.

Adds:
- `DQ-ENTITY-003`: if organism identity is unresolved, suppress downstream containment/PPE/BSL/transport/disposal missing-information items unless the user explicitly asked about those operational domains.
- `DQ-REG-001`: if the user asks about Malaysian Biosafety notification/Form E/Director-General notification and LMO status is not established, preserve the LMO/modern-biotechnology trigger as required missing information and an explicit next step.

No frozen Stage 8 component or integration hook is modified.
