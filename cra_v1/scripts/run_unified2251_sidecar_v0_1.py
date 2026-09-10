import sys
from pathlib import Path

ROOT = Path("/home/khengoon/biosafe")
sys.path.insert(0, str(ROOT / "unified_v1/src"))

from biosafe_unified2251.server import app

app.run(host="127.0.0.1", port=8777, debug=False)
