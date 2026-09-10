from pathlib import Path
P=Path(__file__).resolve().parent.parent;j=(P/"assets"/"biosafe_conversational_shell.js").read_text();c=(P/"assets"/"biosafe_conversational_shell.css").read_text()
C=[("sidebar","biosafe-chat-sidebar" in j),("new-chat","+ New conversation" in j),("modes",all(x in j for x in ["Ask BioSafe","Review Document","Form E Assistant"])),("stream","biosafe-chat-stream" in j),("user","biosafe-user-bubble" in j),("assistant","assistantTurn" in j),("composer","biosafe-chat-composer" in j),("dom",all(x in j for x in ['getElementById("ask")','getElementById("review")','getElementById("forme")'])),("file",'getElementById("reviewFile")' in j),("boundary","does not make an IBC determination" in j),("mobile","@media(max-width:760px)" in c),("no-fetch","fetch(" not in j),("runtime","Local • Qwen" in j),("api","BioSafeConversationalShell" in j)]
bad=[]
for n,o in C:print(("PASS" if o else "FAIL"),n);bad+=[] if o else [n]
print(f"\nSummary: {len(C)-len(bad)}/{len(C)} passed")
if bad:raise SystemExit(str(bad))
print("Stage 10.3 conversational-shell static regression: PASS")
