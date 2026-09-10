
import json,urllib.request,urllib.error,re

BASE_A="http://127.0.0.1:8768"
BASE_B="http://127.0.0.1:8769"

cases=[
 ("identity","who are you"),
 ("self_knowledge","do u know who i am?"),
 ("definition","What is biosafety?"),
 ("comparison","What is the difference between biosafety and biosecurity?"),
 ("acronyms","What is PI and IBC?"),
 ("malaysia_scope","Does Act 678 apply to every laboratory in Malaysia?"),
 ("anthracis","I work with Bacillus anthracis. Do I need to notify the Director General?"),
]

def post(base,q,sid=None):
    p={"query":q}
    if sid:p["session_id"]=sid
    req=urllib.request.Request(base+"/api/ask",data=json.dumps(p).encode(),method="POST",
        headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=240) as r:
        return r.getcode(),json.loads(r.read().decode())

def text(o):
    parts=[]
    def walk(x,k=""):
        if k.startswith("_"): return
        if isinstance(x,dict):
            for a,b in x.items(): walk(b,a)
        elif isinstance(x,list):
            for a in x: walk(a,k)
        elif isinstance(x,str): parts.append(x)
    walk(o); return "\n".join(parts)

def hygiene(t):
    low=t.lower()
    bad=("does not require a new regulatory retrieval","activated_domains","task_frame","frozen_domain_adapter")
    return not any(x in low for x in bad)

print("BioSafe Unified-2.2 A/B response regression")
passes=0; total=0
sidA=sidB=None
for name,q in cases:
    sA,a=post(BASE_A,q,sidA); sidA=a.get("session_id",sidA)
    sB,b=post(BASE_B,q,sidB); sidB=b.get("session_id",sidB)
    tA=text(a); tB=text(b)
    print("\n==",name,"==")
    print("A(8768):",tA[:1200].replace("\n"," | "))
    print("B(8769):",tB[:1200].replace("\n"," | "))
    checks=[
      ("http",sA==200 and sB==200),
      ("B_hygiene",hygiene(tB)),
      ("B_nonempty",len(tB.strip())>0),
    ]
    if name in ("definition","comparison","acronyms"):
        checks.append(("B_no_generic_clarification","need more context" not in tB.lower()))
    if name=="anthracis":
        checks.append(("B_no_universal_trigger_claim","because bacillus anthracis" not in tB.lower()))
    for n,c in checks:
        total+=1; passes+=int(bool(c)); print(f"  {n}: {'PASS' if c else 'FAIL'}")
print(f"\nUnified-2.2 A/B hard assertions: {passes}/{total} PASS")
if passes!=total: raise SystemExit(1)
print("Unified-2.2 A/B hard assertions: PASS")
print("NOTE: Human review of A vs B wording is still required before acceptance.")
