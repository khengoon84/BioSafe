
import sys
from pathlib import Path
ROOT=Path("/home/khengoon/biosafe")
sys.path.insert(0,str(ROOT/"unified_v1"/"src"))
from biosafe_unified22.server import app
if __name__=="__main__":
    print("Starting BioSafe Unified-2.2 v0.1 on http://127.0.0.1:8769")
    app.run(host="127.0.0.1",port=8769,debug=False)
