#!/usr/bin/env python3
from __future__ import annotations
import json, socket, subprocess, urllib.request

PORT=11434

def probe(host):
    url=f"http://{host}:{PORT}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=2) as r:
            obj=json.loads(r.read().decode("utf-8"))
        return True, obj
    except Exception:
        return False, None

candidates=["127.0.0.1","localhost"]

# WSL2 default gateway commonly points to the Windows host in NAT mode.
try:
    out=subprocess.check_output(["sh","-lc","ip route | awk '/default/ {print $3; exit}'"], text=True).strip()
    if out and out not in candidates:
        candidates.append(out)
except Exception:
    pass

print("BioSafe Ollama connectivity check")
print("----------------------------------")
for host in candidates:
    ok,obj=probe(host)
    print(f"{host:15} {'OK' if ok else 'not reachable'}")
    if ok:
        models=[m.get("name") or m.get("model") for m in obj.get("models",[])]
        print("  Models:", ", ".join(x for x in models if x) or "(none)")
        print(f"  Recommended BIOSAFE_OLLAMA_HOST=http://{host}:{PORT}")
        raise SystemExit(0)

print("\nOllama was not reachable from WSL2.")
print("Confirm Ollama is running in Windows.")
print("If localhost forwarding is unavailable, Windows Ollama may need to listen on a reachable interface.")
raise SystemExit(2)
