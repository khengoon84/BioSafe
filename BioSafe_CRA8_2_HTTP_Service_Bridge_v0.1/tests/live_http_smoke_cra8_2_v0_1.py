import json, urllib.request
URL="http://127.0.0.1:8766"
def post(path,payload):
    req=urllib.request.Request(
        URL+path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req,timeout=900) as r:
        return r.status,json.loads(r.read().decode("utf-8"))

with urllib.request.urlopen(URL+"/health",timeout=10) as r:
    health=json.loads(r.read().decode("utf-8"))
print("HEALTH",json.dumps(health,indent=2))

status,identity=post("/api/ask",{"query":"who are you?"})
print("IDENTITY",status,json.dumps(identity,indent=2))

status,ask=post("/api/ask",{
    "query":"What general factors should I consider in a biosafety risk assessment?",
    "session_id":identity["session_id"]
})
print("ASK",status,json.dumps({
    "session_id":ask.get("session_id"),
    "route":ask.get("route"),
    "task_frame":ask.get("task_frame"),
    "conclusion":(ask.get("response") or {}).get("conclusion"),
    "bridge":ask.get("_cra_bridge")
},indent=2))

assert health["bridge"]=="CRA-8.2-v0.1"
assert identity["route"]=="product_help_bypass"
assert ask["route"]=="frozen_domain_adapter"
assert ask["task_frame"]["activated_domains"]==["general_biosafety"]
assert ask["session_id"]==identity["session_id"]
print("CRA-8.2 optional live HTTP smoke: PASS")
