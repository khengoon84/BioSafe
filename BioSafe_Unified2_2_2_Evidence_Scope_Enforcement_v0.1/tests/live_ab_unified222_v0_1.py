
import json,urllib.request
A="http://127.0.0.1:8770";B="http://127.0.0.1:8771"
cases=[("identity","who are you"),("self","do u know who i am?"),("definition","What is biosafety?"),
("comparison","What is the difference between biosafety and biosecurity?"),("acronyms","What is PI and IBC?"),
("scope","Does Act 678 apply to every laboratory in Malaysia?"),
("anthracis","I work with Bacillus anthracis. Do I need to notify the Director General?")]
def post(base,q,sid=None):
 d={"query":q}
 if sid:d["session_id"]=sid
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
sa=sb=None;p=t=0
for name,q in cases:
 ca,a=post(A,q,sa);sa=a.get("session_id",sa);cb,b=post(B,q,sb);sb=b.get("session_id",sb)
 ta,tb=text(a),text(b);print(f"\n== {name} ==\nA(8770): {ta[:1500]}\nB(8771): {tb[:1500]}")
 checks=[("http",ca==200 and cb==200),("B_nonempty",bool(tb.strip()))]
 if name=="self":
  checks.append(("self_no_reg_pollution",not any(x.lower() in tb.lower() for x in ("CLM-","IBC Assessment Report","Director General"))))
 if name=="definition":
  checks.append(("definition_no_my_reg_pollution",not any(x.lower() in tb.lower() for x in ("IBC Assessment Report","Director General","Act 678"))))
 if name=="comparison":
  checks.append(("comparison_no_forced_malaysia","current malaysian" not in tb.lower()))
 if name=="scope":checks.append(("scope_not_universal","not" in tb.lower() or "no." in tb.lower()))
 if name=="anthracis":checks.append(("trigger_uncertainty",any(x in tb.lower() for x in ("lmo","modern biotechnology","insufficient"))))
 for n,c in checks:t+=1;p+=int(bool(c));print(f"  {n}: {'PASS' if c else 'FAIL'}")
print(f"\nUnified-2.2.2 A/B hard assertions: {p}/{t} PASS")
if p!=t:raise SystemExit(1)
print("Human wording review remains mandatory.")
