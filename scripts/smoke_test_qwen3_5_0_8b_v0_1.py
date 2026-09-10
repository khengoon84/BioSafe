#!/usr/bin/env python3
import json, urllib.request, time

MODEL = "qwen3.5:0.8b"
HOST = "http://localhost:11434"

payload = {
    "model": MODEL,
    "messages": [{"role":"user","content":"Return JSON only: {\\\"status\\\":\\\"ok\\\",\\\"model\\\":\\\"qwen3.5:0.8b\\\"}"}],
    "stream": False,
    "format": "json",
    "options": {"temperature": 0.0, "num_predict": 80},
}
req = urllib.request.Request(HOST + "/api/chat", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"})
t0=time.perf_counter()
with urllib.request.urlopen(req, timeout=300) as r:
    obj=json.loads(r.read().decode())
wall=time.perf_counter()-t0
content=(obj.get("message") or {}).get("content", "")
print("Model:", MODEL)
print("Wall seconds:", round(wall,3))
print("Done reason:", obj.get("done_reason"))
print("Content:", content)
try:
    print("Parsed JSON:", json.loads(content))
except Exception as e:
    raise SystemExit("Smoke test failed: output was not valid JSON: " + str(e))
print("SMOKE TEST PASS")
