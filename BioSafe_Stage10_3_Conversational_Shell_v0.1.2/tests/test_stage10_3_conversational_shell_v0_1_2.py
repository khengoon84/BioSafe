from pathlib import Path
P=Path(__file__).resolve().parent.parent
j=(P/"assets"/"biosafe_conversational_shell.js").read_text()
c=(P/"assets"/"biosafe_conversational_shell.css").read_text()

checks=[
("no-duplicate-turn-labels",'biosafe-turn-label' not in j),
("clear-editor-function","function clearEditor()" in j),
("clear-after-submit","clearEditor();\n  if(b) b.click();" in j),
("simple-primary-answer","biosafe-primary-answer" in j),
("secondary-details-collapsed","biosafe-secondary-details" in j and "More details" in j),
("developer-details-collapsed","biosafe-developer-details" in j and "Developer details" in j),
("legacy-host-zero-layout","clip-path:inset(100%)" in c and "width:0!important" in c),
("preserve-original-controls","biosafe-stage9-hidden-host" in j),
("no-live-output-relocation","b.append(out)" not in j),
("mirror-output","mirrorOutput" in j),
("incomplete-query-guard","incompleteAsk" in j),
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
print("Stage 10.3 v0.1.2 static regression: PASS")
