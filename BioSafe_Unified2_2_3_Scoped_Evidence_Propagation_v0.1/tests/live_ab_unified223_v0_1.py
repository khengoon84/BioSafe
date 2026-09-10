import json,urllib.request
A="http://127.0.0.1:8771";B="http://127.0.0.1:8772"
cases=[("identity","who are you"),("self","do u know who i am?"),("definition","What is biosafety?"),
("comparison","What is the difference between biosafety and biosecurity?"),("acronyms","What is PI and IBC?"),
("scope","Does Act 678 apply to every laboratory in Malaysia?"),
("anthracis","I work with Bacillus anthracis. Do I need to notify the Director General?")]
def post(base,q,sid=None):
 d={"query":q};d.update({"session_id":sid} if sid else {})
 req=urllib.request.Request(base+"/api/ask",data=json.dumps(d).encode(),method="POST",headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=240) as r:return r.getcode(),json.loads(r.read().decode())
def text(o):
 out=[]
 def w(x,k=""):
  if k.startswith("_"):return
  if isinstance(x,dict):
   for a,b in x.items():w(b,a)
  elif isinstance(x,list):
   for a in x:w(a,k)
  elif isinstance(x,str):out.append(x)
 w(o);return " | ".join(out)
sa=sb=None;P=T=0
for name,q in cases:
 ca,a=post(A,q,sa);sa=a.get("session_id",sa);cb,b=post(B,q,sb);sb=b.get("session_id",sb)
 tb=text(b);print(f"\n== {name} ==\nA(8771): {text(a)[:1500]}\nB(8772): {tb[:1500]}")
 checks=[("http",ca==200 and cb==200),("B_nonempty",bool(tb.strip()))]
 if name=="self":checks+= [("self_clean",not any(x.lower() in tb.lower() for x in ("CLM-","IBC Assessment Report","Director General")))]
 if name=="definition":checks+=[("definition_no_my_reg",not any(x.lower() in tb.lower() for x in ("IBC Assessment Report","Act 678","Director General")))]
 if name=="comparison":checks+=[("comparison_no_forced_malaysia","current malaysian" not in tb.lower())]
 if name=="acronyms":checks+=[("ibc_not_regulatory_body","regulatory body" not in tb.lower())]
 if name=="scope":checks+=[("scope_not_universal","not" in tb.lower() or "no." in tb.lower())]
 if name=="anthracis":checks+=[("trigger_uncertainty",any(x in tb.lower() for x in ("lmo","modern biotechnology","insufficient")))]
 for n,c in checks:T+=1;P+=int(c);print(f"  {n}: {'PASS' if c else 'FAIL'}")
print(f"\nUnified-2.2.3 A/B hard assertions: {P}/{T} PASS")
if P!=T:raise SystemExit(1)
print("Human wording/provenance review remains mandatory.")
