from pathlib import Path
P=Path(__file__).resolve().parent.parent
j=(P/"assets"/"biosafe_conversational_shell.js").read_text()
c=(P/"assets"/"biosafe_conversational_shell.css").read_text()

checks=[
("preserve-original-controls","biosafe-stage9-hidden-host" in j),
("no-move-output-into-turn","b.append(out)" not in j),
("mirror-output","mirrorOutput" in j),
("stage10-renderer-hook","BioSafeResponseRenderer" in j),
("original-button-click","originalButton(activeMode)" in j and "b.click()" in j),
("ask-incomplete-guard","incompleteAsk" in j),
("who-guard","who|what|when|where|why|how" in j),
("single-short-fragment-guard","words.length===1" in j),
("three-modes",all(x in j for x in ["Ask BioSafe","Review Document","Form E Assistant"])),
("composer","biosafe-chat-composer" in j),
("review-file-proxy","reviewFileProxy" in j),
("forme-boundary","does not make an IBC determination" in j),
("mobile","@media(max-width:760px)" in c),
("no-fetch","fetch(" not in j),
]
bad=[]
for n,o in checks:
    print(("PASS" if o else "FAIL"),n)
    if not o: bad.append(n)
print(f"\nSummary: {len(checks)-len(bad)}/{len(checks)} passed")
if bad: raise SystemExit("Failures: "+", ".join(bad))
print("Stage 10.3 v0.1.1 static regression: PASS")
