# BioSafe CRA-8.4 — Browser/UI Binding v0.1

Binds the existing ChatGPT-style BioSafe UI on **127.0.0.1:8765** to the validated CRA-8.3.1 sidecar on **127.0.0.1:8767** through same-origin proxy routes.

## What changes

- adds `/api/cra/health`, `/api/cra/ask`, `/api/cra/review`, `/api/cra/form-e`, `/api/cra/session/reset`;
- browser Ask/Review/Form E calls those CRA routes;
- browser stores the CRA `session_id` in `localStorage`;
- **+ New conversation** resets that CRA session;
- CRA `direct_answer` renders correctly;
- `_cra_adapter`, `_cra_quality`, `_meta` are hidden from the ordinary-user mirror;
- old `/api/ask`, `/api/review`, `/api/form-e` remain untouched for rollback;
- timestamped backups are made of every modified live file.

## Install

```bash
cd /home/khengoon/biosafe
source .venv/bin/activate

cd /home/khengoon/biosafe/BioSafe_CRA8_4_Browser_UI_Binding_v0.1
python scripts/install_cra8_4_v0_1.py
```

## Runtime

Keep CRA-8.3.1 running on port 8767.

Restart the UI server on port 8765. If you use the Stage 9 shell directly:

```bash
cd /home/khengoon/biosafe/stage9_local_shell/app
python main.py
```

## Live proxy test

```bash
/home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/live_smoke_cra8_4_proxy_v0_1.py
```

Expected: `CRA-8.4 live proxy smoke: PASS`

## Browser validation

Open `http://127.0.0.1:8765` and test:

1. `who are you?`
2. general biosafety risk-assessment question;
3. a transport question;
4. follow with `Why does that matter?`;
5. click **+ New conversation** and ask `who are you?`;
6. Review Document;
7. Form E Assistant.

Internal CRA metadata should not be visible.
