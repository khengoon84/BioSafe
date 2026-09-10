import json, urllib.request
BASE="http://127.0.0.1:8765"

def get(path):
    with urllib.request.urlopen(BASE+path,timeout=20) as r:
        return r.status,json.loads(r.read().decode())

def post(path,payload,timeout=900):
    req=urllib.request.Request(
        BASE+path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.status,json.loads(r.read().decode())

status,h=get("/api/cra/health")
print("HEALTH",status,json.dumps(h,indent=2))
assert status==200 and h.get("bridge")=="CRA-8.3.1-v0.1"

status,a=post("/api/cra/ask",{"query":"who are you?"})
print("IDENTITY",status,json.dumps({"session_id":a.get("session_id"),"route":a.get("route")},indent=2))
assert status==200 and a.get("route")=="product_help_bypass"
sid=a.get("session_id")
assert sid

status,b=post("/api/cra/ask",{
    "query":"What general factors should I consider in a biosafety risk assessment?",
    "session_id":sid,
})
print("ASK",status,json.dumps({
    "session_id":b.get("session_id"),
    "route":b.get("route"),
    "task_frame":b.get("task_frame"),
},indent=2))
assert status==200
assert b.get("session_id")==sid
assert b.get("route")=="frozen_domain_adapter"
assert (b.get("task_frame") or {}).get("activated_domains")==["general_biosafety"]

status,r=post("/api/cra/session/reset",{"session_id":sid},timeout=30)
print("RESET",status,json.dumps(r,indent=2))
assert status==200 and r.get("reset") is True

print("CRA-8.4 live proxy smoke: PASS")
