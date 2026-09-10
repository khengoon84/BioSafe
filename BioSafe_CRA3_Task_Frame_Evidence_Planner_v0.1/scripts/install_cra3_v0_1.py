from pathlib import Path
import shutil

SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")
(TARGET/"src").mkdir(parents=True,exist_ok=True)
(TARGET/"tests").mkdir(parents=True,exist_ok=True)

for rel in [
    "src/task_frame_builder_v0_1.py",
    "src/evidence_requirement_planner_v0_1.py",
    "src/retrieval_request_adapter_v0_1.py",
    "tests/test_cra3_task_frame_evidence_v0_1.py",
]:
    s=SRC/rel; d=TARGET/rel
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(s,d)

print("CRA-3 installed to:",TARGET)
print("CRA-1/CRA-2 reused. No frozen Stage 8/9 files modified.")
print("Run:")
print("  /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra3_task_frame_evidence_v0_1.py")
