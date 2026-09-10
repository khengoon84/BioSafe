# BioSafe CRA-2 — Interaction + State Engine v0.1

Implements the generalized conversational state layer defined in CRA v1.0.

## Components
- Interaction Manager v0.1
- Conversation / Case State Manager v0.1
- Reference Resolver v0.1
- Clarification Resolver v0.1
- Interaction + State Engine v0.1

## Behaviors validated
- Product/help questions bypass regulatory domain processing.
- Identity questions are product-help interactions.
- Short answers resolve pending clarification slots.
- "why?", "what approval did you mean?", and similar references bind to recent assistant concepts.
- Confirmed facts carry provenance and cannot be silently overwritten.
- Conflicts become `disputed`.
- Domain activation/deactivation is explicit.
- Reformulation and task changes are distinct interaction types.

This engine is isolated and **not yet wired into the live browser UI**.

## Install
```bash
cd /home/khengoon/biosafe/BioSafe_CRA2_Interaction_State_Engine_v0.1
python scripts/install_cra2_v0_1.py
```

## Test
```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra2_interaction_state_v0_1.py
```
