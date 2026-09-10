from pathlib import Path
p=Path(__file__).resolve().parent.parent/"src"/"cra_bridge_app_v0_1.py"
text=p.read_text(encoding="utf-8")
compile(text,str(p),"exec")
required=[
    '@app.get("/health")',
    '@app.post("/api/ask")',
    '@app.post("/api/review")',
    '@app.post("/api/form-e")',
    '@app.post("/api/session/reset")',
    'port=8766',
    '"live_ui_modified":False',
]
checks=[x in text for x in required]
for x,ok in zip(required,checks):
    print(("PASS" if ok else "FAIL"),x)
print(f"\nSummary: {sum(checks)}/{len(checks)} passed")
if not all(checks): raise SystemExit(1)
print("CRA-8.2 static HTTP contract v0.1: PASS")
