import json,urllib.request
A="http://127.0.0.1:8772";B="http://127.0.0.1:8773"
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
 tb=text(b);print(f"\\n== {name} ==\\nA(8772): {text(a)[:1500]}\\nB(8773): {tb[:1500]}")
 checks=[("http",ca==200 and cb==200),("B_nonempty",bool(tb.strip()))]
 if name=="definition":checks+=[("definition_no_reg_workflow",not any(x in tb.lower() for x in ("current malaysian","identify the specific hazard","document review is advisory")))]
 if name=="comparison":checks+=[("comparison_no_forced_malaysia","current malaysian" not in tb.lower()),("comparison_no_reg_nextstep","relevant malaysian regulatory framework" not in tb.lower())]
 if name=="acronyms":checks+=[("ibc_present","institutional biosafety committee" in tb.lower()),("ibc_not_regulatory_body","regulatory body" not in tb.lower())]
 if name=="scope":checks+=[("scope_not_universal","not" in tb.lower() or "no." in tb.lower())]
 if name=="anthracis":checks+=[("trigger_uncertainty",any(x in tb.lower() for x in ("lmo","modern biotechnology","insufficient")))]
 for n,c in checks:T+=1;P+=int(c);print(f"  {n}: {'PASS' if c else 'FAIL'}")
print(f"\\nUnified-2.2.4 A/B hard assertions: {P}/{T} PASS")
if P!=T:raise SystemExit(1)
print("Human wording/provenance review remains mandatory.")
