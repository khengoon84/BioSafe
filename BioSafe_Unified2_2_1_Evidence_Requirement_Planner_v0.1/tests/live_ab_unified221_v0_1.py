
import json,urllib.request
A="http://127.0.0.1:8769"; B="http://127.0.0.1:8770"
cases=[
 ("identity","who are you"),
 ("self_knowledge","do u know who i am?"),
 ("definition","What is biosafety?"),
 ("comparison","What is the difference between biosafety and biosecurity?"),
 ("acronyms","What is PI and IBC?"),
 ("scope","Does Act 678 apply to every laboratory in Malaysia?"),
 ("anthracis","I work with Bacillus anthracis. Do I need to notify the Director General?")
]
def post(base,q,sid=None):
    d={"query":q}
    if sid:d["session_id"]=sid
    req=urllib.request.Request(base+"/api/ask",data=json.dumps(d).encode(),method="POST",headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=240) as r:return r.getcode(),json.loads(r.read().decode())
def txt(o):
    parts=[]
    def w(x,k=""):
        if k.startswith("_"):return
        if isinstance(x,dict):
            for a,b in x.items():w(b,a)
        elif isinstance(x,list):
            for a in x:w(a,k)
        elif isinstance(x,str):parts.append(x)
    w(o);return " | ".join(parts)
sidA=sidB=None; passed=total=0
for name,q in cases:
    sa,a=post(A,q,sidA); sidA=a.get("session_id",sidA)
    sb,b=post(B,q,sidB); sidB=b.get("session_id",sidB)
    ta,tb=txt(a),txt(b)
    print(f"\n== {name} =="); print("A(8769):",ta[:1400]); print("B(8770):",tb[:1400])
    checks=[("http",sa==200 and sb==200),("B_nonempty",bool(tb.strip()))]
    if name in ("identity","self_knowledge"):
        bad=("CLM-","Director General","IBC Assessment Report","Emergency response")
        checks.append(("B_no_regulatory_pollution",not any(x.lower() in tb.lower() for x in bad)))
    if name=="scope":
        checks.append(("B_says_not_universal",("not" in tb.lower() or "no." in tb.lower())))
    if name=="anthracis":
        checks.append(("B_preserves_trigger_uncertainty",("lmo" in tb.lower() or "modern biotechnology" in tb.lower() or "insufficient" in tb.lower())))
    for n,c in checks:
        total+=1;passed+=int(bool(c));print(f"  {n}: {'PASS' if c else 'FAIL'}")
print(f"\nUnified-2.2.1 A/B hard assertions: {passed}/{total} PASS")
if passed!=total:raise SystemExit(1)
print("Unified-2.2.1 A/B hard assertions: PASS")
print("NOTE: Human response-quality review remains mandatory.")
