
from pathlib import Path
import sys, urllib.request, json, importlib.util

print("Python:",sys.version.split()[0])
for mod in ["numpy","scipy","sklearn"]:
    print(f"{mod}:", "OK" if importlib.util.find_spec(mod) else "MISSING")
try:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags",timeout=3) as r:
        obj=json.loads(r.read().decode())
    print("Ollama: OK")
    print("Models:",", ".join((m.get("name") or m.get("model","")) for m in obj.get("models",[])) or "(none)")
except Exception as e:
    print("Ollama: NOT REACHABLE")
    print("Detail:",e)
