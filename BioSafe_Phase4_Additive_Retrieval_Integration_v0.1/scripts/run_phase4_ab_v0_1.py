from pathlib import Path
import json,sys
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE/"src"))
from phase4_ab import evaluate
(HERE/"reports").mkdir(exist_ok=True)
report=evaluate();(HERE/"reports/phase4_ab_report_v0_1.json").write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
print(f"C4 additive retrieval integration: result={report['result']}")