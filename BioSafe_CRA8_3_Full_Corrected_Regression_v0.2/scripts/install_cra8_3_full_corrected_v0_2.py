from pathlib import Path
import shutil

SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")

for sub in ["tests","fixtures","reports"]:
    (TARGET/sub).mkdir(parents=True,exist_ok=True)

for rel in [
    "tests/run_cra8_3_full_corrected_regression_v0_2.py",
    "fixtures/sample_review_sop.txt",
]:
    src=SRC/rel
    dst=TARGET/rel
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)

print("CRA-8.3 full corrected regression installed to:",TARGET)
print("No runtime, frozen inference, or browser/UI file was modified.")
print("Run this only while CRA-8.3.1 corrected sidecar is active on 127.0.0.1:8767.")
