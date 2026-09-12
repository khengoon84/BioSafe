from pathlib import Path
import json
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE/"src"))
from environment_preflight import evaluate

(HERE/"reports").mkdir(exist_ok=True)
report=evaluate()
(HERE/"reports/c5_environment_preflight_report_v0_1.json").write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
print(f"C5 environment preflight: result={report['result']}")