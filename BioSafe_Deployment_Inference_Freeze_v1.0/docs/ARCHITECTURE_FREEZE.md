# BioSafe Deployment Inference Architecture v1.0 — FROZEN

```text
User query / uploaded document(s)
    ↓
Hard Safety Gate
    ↓
Policy & Decision Guard v0.3.2
    ↓
Authority Router v0.1 + Query Router v0.2
    ↓
Scope Gate v0.2.1
    ↓
CFG-02 RAG + BioSafe KB v0.2
    ↓
Structured Document Analysis Layer v1.0 [FROZEN]
    ↓
Complexity/Escalation Router v0.1 [FROZEN]
    ├── routine / single-document → Qwen3.5-0.8B
    └── complex / contradiction / failure → Qwen3.5-2B
    ↓
Context Budget Manager v0.2
    ↓
Qwen3.5 compact reasoning output
    ↓
Deterministic Response Assembler v0.1
    ↓
Regulatory Language Guard v0.1.1 [FROZEN]
    ↓
Existing output / boundary validators
    ↓
Final BioSafe response
```

## Model policy

Qwen3.5-0.8B is the primary runtime.

Qwen3.5-2B is an escalation runtime for concrete complexity or failure signals.

## Freeze principle

A cosmetic wording issue or isolated model variation is not sufficient reason to reopen this architecture.
A future change requires a reproducible benchmark failure that can be traced to a frozen component.
