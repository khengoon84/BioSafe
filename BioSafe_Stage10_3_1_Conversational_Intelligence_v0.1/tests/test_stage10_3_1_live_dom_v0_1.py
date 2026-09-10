from pathlib import Path
R=Path("/home/khengoon/biosafe/stage9_local_shell")
p=next((x for x in [R/"app"/"templates"/"index.html",R/"templates"/"index.html"] if x.exists()),None)
if not p: raise SystemExit("No index.html")
h=p.read_text(encoding="utf-8")
req=[
'id="askQuery"','id="reviewQuery"','id="formEQuery"','id="output"',
'biosafe_conversational_shell.css','biosafe_conversational_shell.js',
'biosafe_conversational_intelligence.css','biosafe_conversational_intelligence.js'
]
bad=[]
for x in req:
    ok=x in h
    print(("PASS" if ok else "FAIL"),x)
    if not ok: bad.append(x)
print(f"\nSummary: {len(req)-len(bad)}/{len(req)} passed")
if bad: raise SystemExit("Missing: "+", ".join(bad))
print("Stage 10.3.1 live DOM compatibility: PASS")
