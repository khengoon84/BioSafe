from pathlib import Path
P=Path(__file__).resolve().parent.parent
j=(P/"assets"/"biosafe_conversational_intelligence.js").read_text()
c=(P/"assets"/"biosafe_conversational_intelligence.css").read_text()

checks=[
("greeting-intent","greeting:" in j),
("identity-intent","identity:" in j),
("capability-intent","capability:" in j),
("local-capability-answer","I can help you understand biosafety and biosecurity requirements" in j),
("conversation-storage","biosafeConversationState_v01" in j),
("follow-up-context","buildContextualQuery" in j and "Current user follow-up" in j),
("pending-info-context","BioSafe asked for clarification about" in j),
("lmo-guard","applyLmoSafeguard" in j and "DQ_LMO_001" in j),
("lmo-definition-logic","novel combination of genetic material" in j),
("educational-layer","educationalSections" in j),
("why-this-matters","Why this matters" in j),
("what-i-need","What I need from you" in j),
("what-next","What to do next" in j),
("no-fetch","fetch(" not in j),
("local-only","localStorage" in j),
("education-css","biosafe-education-section" in c),
]
bad=[]
for n,o in checks:
    print(("PASS" if o else "FAIL"),n)
    if not o: bad.append(n)
print(f"\nSummary: {len(checks)-len(bad)}/{len(checks)} passed")
if bad: raise SystemExit("Failures: "+", ".join(bad))
print("Stage 10.3.1 static regression: PASS")
