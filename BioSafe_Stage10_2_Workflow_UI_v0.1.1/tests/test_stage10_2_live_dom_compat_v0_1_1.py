from pathlib import Path
ROOT=Path("/home/khengoon/biosafe/stage9_local_shell")
templates=[ROOT/"app"/"templates"/"index.html",ROOT/"templates"/"index.html"]
template=next((p for p in templates if p.exists()),None)
if template is None: raise SystemExit("FAIL no Stage 9 index.html found")
html=template.read_text(encoding="utf-8")
checks=[
 ("stage9-ask",'id="ask"' in html),
 ("stage9-review",'id="review"' in html),
 ("stage9-forme",'id="forme"' in html),
 ("stage9-askQuery",'id="askQuery"' in html),
 ("stage9-reviewFile",'id="reviewFile"' in html),
 ("stage9-reviewQuery",'id="reviewQuery"' in html),
 ("stage9-formEQuery",'id="formEQuery"' in html),
 ("stage9-status",'id="status"' in html),
 ("stage9-output",'id="output"' in html),
 ("stage10-css-linked","biosafe_workflow_ui.css" in html),
 ("stage10-js-linked","biosafe_workflow_ui.js" in html),
]
failed=[]
for name,ok in checks:
    print(("PASS" if ok else "FAIL"),name)
    if not ok: failed.append(name)
print(f"\nSummary: {len(checks)-len(failed)}/{len(checks)} passed")
if failed: raise SystemExit("Failures: "+", ".join(failed))
print("Stage 10.2 v0.1.1 live DOM compatibility: PASS")
