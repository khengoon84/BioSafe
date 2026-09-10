# BioSafe Stage 10.3 — Conversational Shell v0.1.4

Focused fix for the legacy Stage 9 layout appearing below the conversational shell.

Changes:
- locks page scrolling to the conversational application viewport;
- fixes the BioSafe chat shell to the full browser viewport;
- moves the legacy Stage 9 host far off-screen and applies strict CSS containment;
- hides any non-chat legacy body siblings;
- adds a defensive legacy-sibling quarantine at runtime;
- preserves the original Stage 9 handlers and API path;
- retains the v0.1.3 submission-order and repeated-query fixes;
- no inference, RAG, routing, guard, validator, model, or API changes.
