import sys
from pathlib import Path
PROJECT=Path("/home/khengoon/biosafe"); sys.path.insert(0,str(PROJECT/"unified_v1"/"src"))
from biosafe_unified2.server import app,PORT
if __name__=="__main__":
    print(f"Starting BioSafe Unified-2 v0.1 on http://127.0.0.1:{PORT}"); print("Downstream expected: CRA-8.4.1 on http://127.0.0.1:8767"); app.run(host="127.0.0.1",port=PORT,debug=False)
