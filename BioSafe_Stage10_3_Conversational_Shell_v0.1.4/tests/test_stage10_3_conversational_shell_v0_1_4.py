from pathlib import Path
P=Path(__file__).resolve().parent.parent
j=(P/"assets"/"biosafe_conversational_shell.js").read_text()
c=(P/"assets"/"biosafe_conversational_shell.css").read_text()

checks=[
("html-scroll-locked","html.biosafe-chat-active" in c and "overflow:hidden!important" in c),
("body-scroll-locked","body.biosafe-chat-mode" in c and "overflow:hidden!important" in c),
("chat-app-fixed-viewport","position:fixed!important" in c and "height:100vh!important" in c),
("legacy-host-offscreen","left:-100000px!important" in c and "top:-100000px!important" in c),
("legacy-host-containment","contain:strict!important" in c),
("legacy-host-clipped","clip-path:inset(50%)!important" in c),
("hide-non-chat-siblings",'body.biosafe-chat-mode > *:not(.biosafe-chat-app):not(.biosafe-stage9-hidden-host)' in c),
("html-class-added",'document.documentElement.classList.add("biosafe-chat-active")' in j),
("legacy-quarantine-helper","function quarantineLegacySiblings" in j),
("legacy-quarantine-called","quarantineLegacySiblings(app,host);" in j),
("preserve-original-handlers","originalButton(modeAtSubmit)" in j),
("no-fetch","fetch(" not in j),
("composer-clear-fix","clearHiddenSourceLater(modeAtSubmit)" in j),
("three-modes",all(x in j for x in ["Ask BioSafe","Review Document","Form E Assistant"])),
]
bad=[]
for name,ok in checks:
    print(("PASS" if ok else "FAIL"),name)
    if not ok: bad.append(name)
print(f"\nSummary: {len(checks)-len(bad)}/{len(checks)} passed")
if bad: raise SystemExit("Failures: "+", ".join(bad))
print("Stage 10.3 v0.1.4 layout isolation regression: PASS")
