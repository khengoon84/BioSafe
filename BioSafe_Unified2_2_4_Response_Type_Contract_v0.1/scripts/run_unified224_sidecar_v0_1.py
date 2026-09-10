import sys
from pathlib import Path
R=Path("/home/khengoon/biosafe");sys.path.insert(0,str(R/"unified_v1/src"))
from biosafe_unified224.server import app
app.run(host="127.0.0.1",port=8773,debug=False)
