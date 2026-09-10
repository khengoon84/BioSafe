from pathlib import Path
import shutil

SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")
for sub in ["src","tests"]:
    (TARGET/sub).mkdir(parents=True,exist_ok=True)

for rel in [
    "src/cra_product_integration_v0_1.py",
    "tests/test_cra8_product_integration_v0_1.py",
]:
    s=SRC/rel; d=TARGET/rel
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(s,d)

print("CRA-8 integration scaffold installed to:",TARGET)
print("No live Flask/UI file and no frozen Stage 8/9 component was modified.")
print("Run:")
print("  /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra8_product_integration_v0_1.py")
