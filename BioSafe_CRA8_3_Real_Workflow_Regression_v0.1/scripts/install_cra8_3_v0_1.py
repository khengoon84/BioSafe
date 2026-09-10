from pathlib import Path
import shutil

SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")

for sub in ["tests","fixtures","reports"]:
    (TARGET/sub).mkdir(parents=True,exist_ok=True)

for rel in [
    "tests/run_cra8_3_workflow_regression_v0_1.py",
    "tests/cra8_3_cases_v0_1.json",
    "fixtures/sample_review_sop.txt",
]:
    src=SRC/rel
    dst=TARGET/rel
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)

print("CRA-8.3 installed to:",TARGET)
print("No frozen inference files, CRA runtime files, or browser/UI files were modified.")
print("Run with CRA-8.2 sidecar already running on 127.0.0.1:8766.")
