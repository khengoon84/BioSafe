from pathlib import Path
R=Path("/home/khengoon/biosafe/stage9_local_shell")
p=next((x for x in [R/"app"/"templates"/"index.html",R/"templates"/"index.html"] if x.exists()),None)
if not p: raise SystemExit("No index.html")
h=p.read_text()
req=[
'id="ask"','id="review"','id="forme"','id="askQuery"','id="reviewFile"',
'id="reviewQuery"','id="formEQuery"','id="status"','id="output"',
'onclick="runAsk()"','onclick="runReview()"','onclick="runFormE()"',
'biosafe_conversational_shell.css','biosafe_conversational_shell.js'
]
bad=[]
for x in req:
    o=x in h
    print(("PASS" if o else "FAIL"),x)
    if not o: bad.append(x)
print(f"\nSummary: {len(req)-len(bad)}/{len(req)} passed")
if bad: raise SystemExit("Missing: "+", ".join(bad))
print("Stage 10.3 v0.1.2 live DOM/handler compatibility: PASS")
