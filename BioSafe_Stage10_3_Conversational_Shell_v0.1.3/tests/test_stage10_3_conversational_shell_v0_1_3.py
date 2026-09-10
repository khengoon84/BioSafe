from pathlib import Path
import re
P=Path(__file__).resolve().parent.parent
j=(P/"assets"/"biosafe_conversational_shell.js").read_text()
c=(P/"assets"/"biosafe_conversational_shell.css").read_text()
m=re.search(r'function submitActive\(\)\{(.*?)\n\}',j,re.S)
submit=m.group(1) if m else ""
checks=[
("submit-function-found",bool(m)),
("handler-before-visible-clear",submit.find("b.click();")!=-1 and submit.find("clearVisibleEditor();",submit.find("addUserTurn"))>submit.find("b.click();")),
("deferred-hidden-clear","function clearHiddenSourceLater(mode)" in j and "setTimeout" in j),
("no-hidden-clear-before-click",'if(src) src.value="";' not in submit),
("no-last-output-dedupe","lastRawOutput" not in j),
("repeat-output-supported","Repeated identical responses" in j),
("incomplete-query-guard","incompleteAsk" in j),
("simple-primary-answer","biosafe-primary-answer" in j),
("secondary-details-collapsed","More details" in j),
("legacy-host-zero-layout","clip-path:inset(100%)" in c),
("preserve-original-controls","biosafe-stage9-hidden-host" in j),
("three-modes",all(x in j for x in ["Ask BioSafe","Review Document","Form E Assistant"])),
("forme-boundary","does not make an IBC determination" in j),
("no-fetch","fetch(" not in j),
]
bad=[]
for n,o in checks:
    print(("PASS" if o else "FAIL"),n)
    if not o: bad.append(n)
print(f"\nSummary: {len(checks)-len(bad)}/{len(checks)} passed")
if bad: raise SystemExit("Failures: "+", ".join(bad))
print("Stage 10.3 v0.1.3 static regression: PASS")
