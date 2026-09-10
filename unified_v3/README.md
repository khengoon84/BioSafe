# Unified-3 Ask BioSafe UI

Single-page conversational interface for BioSafe. This is the Unified-3 UI referenced in `Project_Baseline.md` Phase B.

## Design principles

- **One visible mode:** Ask BioSafe. Document Review and Form E are internal capabilities selected from intent and attachments — there are no separate tabs.
- **No internal metadata:** Routing, guard, confidence, task-frame, and evidence-control fields are never shown to the user.
- **Sources are expandable:** Evidence and authority are hidden behind a "Show sources" toggle by default.
- **Attachments:** Text documents are sent for document analysis. PNG/JPEG images are sent as local base64 payloads to the sidecar's vision route; images are not passed through the text-document adapter.
- **Conversation state:** Maintained via `session_id`, including an active subject/concept for genuine elaboration and continuation turns. "New Conversation" resets conversation and case state in the browser session.

## Architecture

```
Browser (Unified-3 UI, port 8778)
        |
        | POST /api/ask
        v
Unified-2.2.5.1 sidecar (port 127.0.0.1:8777)
        |
        | Ollama API
        v
Local Ollama (127.0.0.1:11434)
```

The configured text models are `qwen3.5:0.8b` (primary) and `qwen3.5:2b` (escalation). Both installed tags report Ollama's `vision` capability. Image observations use `qwen3.5:2b` and remain local. CPU-only image inference can be noticeably slower than deterministic conversation turns; a 96×96 live probe took approximately 24 seconds through the full UI/sidecar path on the tested WSL2 environment.

The UI is a single `index.html` file with embedded CSS and JavaScript. No build step, no framework, no dependencies.

## Running

1. Start the Unified-2.2.5.1 sidecar:

```bash
cd /home/khengoon/biosafe
.venv/bin/python cra_v1/scripts/run_unified2251_sidecar_v0_1.py
```

2. In a separate terminal, start the Unified-3 UI:

```bash
cd /home/khengoon/biosafe
./unified_v3/run_unified3_ui_v0_1.sh
```

3. Open http://127.0.0.1:8778 in your browser.

## API contract

The UI posts to `/api/ask`:

```json
{
  "query": "Do I need a permit for contained use of an LMO?",
  "documents": [{"filename": "protocol.txt", "text": "...document content..."}],
  "session_id": "unified-..."
}
```

An image upload uses the same endpoint:

```json
{
  "query": "What is this image about?",
  "documents": [{
    "filename": "bench.jpg",
    "content_type": "image/jpeg",
    "text": "",
    "image": "data:image/jpeg;base64,...",
    "is_image": true
  }],
  "session_id": "unified-..."
}
```

The sidecar removes the data-URL prefix before sending raw base64 through Ollama's chat `images` field. Image output is model-generated, advisory observation rather than authoritative evidence or a compliance determination.

And renders the response fields: `conclusion`, `direct_answer`, `recommended_next_step`, `recommended_next_steps`, `missing_information`, `limitations`, `safety`, `evidence`, `applicable_authority`.

## Files

| File | Purpose |
|------|---------|
| `index.html` | Single-page UI (HTML + CSS + JS) |
| `run_unified3_ui_v0_1.sh` | Launcher: serves UI on 8778, proxies /api/* to sidecar on 8777 |
| `README.md` | This file |
