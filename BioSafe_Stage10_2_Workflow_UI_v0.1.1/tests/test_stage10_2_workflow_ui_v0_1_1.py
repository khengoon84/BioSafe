from pathlib import Path
PKG=Path(__file__).resolve().parent.parent
js=(PKG/"assets"/"biosafe_workflow_ui.js").read_text(encoding="utf-8")
css=(PKG/"assets"/"biosafe_workflow_ui.css").read_text(encoding="utf-8")
checks=[
    ("ask-config",'id:"ask"' in js),
    ("review-config",'id:"review"' in js),
    ("forme-config",'id:"forme"' in js),
    ("review-file",'getElementById("reviewFile")' in js),
    ("status",'getElementById("status")' in js),
    ("ask-textarea",'"askQuery"' in js),
    ("review-textarea",'"reviewQuery"' in js),
    ("forme-textarea",'"formEQuery"' in js),
    ("tablist",'setAttribute("role","tablist")' in js),
    ("tabpanel",'setAttribute("role","tabpanel")' in js),
    ("keyboard","ArrowRight" in js and "ArrowLeft" in js),
    ("forme-boundary","does not make an IBC determination" in js),
    ("responsive","@media (max-width:720px)" in css),
    ("no-fetch","fetch(" not in js),
]
failed=[]
for name,ok in checks:
    print(("PASS" if ok else "FAIL"),name)
    if not ok: failed.append(name)
print(f"\nSummary: {len(checks)-len(failed)}/{len(checks)} passed")
if failed: raise SystemExit("Failures: "+", ".join(failed))
print("Stage 10.2 v0.1.1 static regression: PASS")
