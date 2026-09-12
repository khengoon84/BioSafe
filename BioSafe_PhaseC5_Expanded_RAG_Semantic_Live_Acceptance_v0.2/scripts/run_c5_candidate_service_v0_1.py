from pathlib import Path
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from candidate_service_v0_1 import app

if __name__=="__main__":
    app.run(host="127.0.0.1",port=8779,debug=False)