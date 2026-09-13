from pathlib import Path
import sys

HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(HERE/"src"),str(HERE/"scripts")]
from phase_c3_7 import canonical_bytes
from provisional_stress import evaluate, owner_review_packet

report=evaluate(); packet=owner_review_packet(report)
(HERE/"reports/provisional_stress_report_v0_1.json").write_bytes(canonical_bytes(report))
(HERE/"reports/provisional_owner_review_packet_v0_1.json").write_bytes(canonical_bytes(packet))
print(f"C3.7 provisional stress: result={report['provisional_result']} gate={report['gate_result']}")