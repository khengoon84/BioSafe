# BioSafe Decision Quality Refinement v0.1.3

Narrow Stage 9 decision-quality correction triggered by a real app regression.

Adds:
- `DQ-ENTITY-002`: unresolved organism identity blocks organism-specific risk-group, BSL, containment, PPE, transport, and disposal conclusions.
- `DQ-GROUND-002`: explicit numerical/classification labels (Risk Group, RG, BSL, Class) are suppressed unless the retrieved evidence supports the same label.

This prevents the observed contradictory output that both asked the user to confirm `Bacillus antracts` and simultaneously treated it as confirmed `Bacillus anthracis` with an unsupported `Class 1.5` label.

No frozen Stage 8 component or integration hook is modified.
