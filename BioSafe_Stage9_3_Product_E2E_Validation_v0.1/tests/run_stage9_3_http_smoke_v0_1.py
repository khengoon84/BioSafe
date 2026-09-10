
from __future__ import annotations
import json
import urllib.request

BASE = "http://127.0.0.1:8765"

def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as r:
        return r.status, json.loads(r.read().decode("utf-8"))

status, health = get("/health")
assert status == 200
assert health.get("status") == "ok"
assert str(health.get("stage", "")).startswith("9")
assert health.get("inference") == "full-local"

payload = json.dumps({"query":"What is the purpose of a biosafety risk assessment?"}).encode("utf-8")
req = urllib.request.Request(
    BASE + "/api/ask",
    data=payload,
    headers={"Content-Type":"application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=180) as r:
    answer = json.loads(r.read().decode("utf-8"))

assert "conclusion" in answer
assert answer.get("_meta", {}).get("model_called") is True
assert answer.get("_meta", {}).get("valid_json_first_pass") is True

print("Stage 9.3 HTTP shell smoke test: PASS")
print("Health:", health)
print("Model:", answer.get("_meta", {}).get("model"))
print("Conclusion:", answer.get("conclusion"))
