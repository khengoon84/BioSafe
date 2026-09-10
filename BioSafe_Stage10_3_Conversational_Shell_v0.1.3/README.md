# BioSafe Stage 10.3 — Conversational Shell v0.1.3

Live-submission race fix.

- Original Stage 9 onclick handler runs before its hidden textarea is cleared.
- Visible chat composer clears immediately after submission.
- Hidden Stage 9 source clears on the next event-loop task.
- Repeated identical outputs are not suppressed.
- All v0.1.2 presentation fixes are retained.
- No inference, RAG, routing, guard, validator, model, or API changes.
