import json,urllib.request
BASE="http://127.0.0.1:8768"
def get(p):
    with urllib.request.urlopen(BASE+p,timeout=10) as r:return r.getcode(),json.loads(r.read().decode())
def post(p,x):
    req=urllib.request.Request(BASE+p,data=json.dumps(x).encode(),method="POST",headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=180) as r:return r.getcode(),json.loads(r.read().decode())
s,h=get("/health"); print("HEALTH",s,json.dumps(h,indent=2)); assert s==200 and h["frozen_core_modified"] is False
s,a=post("/api/ask",{"query":"who are you"}); print("IDENTITY",s,a.get("session_id")); assert s==200; sid=a["session_id"]
s,b=post("/api/ask",{"query":"What is the difference of biosafety and biosecurity?","session_id":sid}); print("EDUCATIONAL",s); assert s==200
s,r=post("/api/session/reset",{"session_id":sid}); print("RESET",s,json.dumps(r,indent=2)); assert s==200 and r["reset"] is True
print("Unified-2 live smoke: PASS")
