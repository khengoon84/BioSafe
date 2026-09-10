
import sys
from pathlib import Path
R=Path("/home/khengoon/biosafe");sys.path.insert(0,str(R/"unified_v1/src"))
from biosafe_unified222.server import app
if __name__=="__main__":
 print("Starting BioSafe Unified-2.2.2 v0.1 on http://127.0.0.1:8771")
 app.run(host="127.0.0.1",port=8771,debug=False)
