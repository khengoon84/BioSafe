from pathlib import Path
import shutil

SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")
for sub in ["src","tests"]:
    (TARGET/sub).mkdir(parents=True,exist_ok=True)

for rel in [
    "src/frozen_inference_rag_adapter_v0_1.py",
    "tests/test_cra8_1_frozen_adapter_v0_1.py",
    "tests/live_smoke_cra8_1_frozen_adapter_v0_1.py",
]:
    s=SRC/rel; d=TARGET/rel
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(s,d)

print("CRA-8.1 installed to:",TARGET)
print("No frozen src/*.py file and no live Flask/UI file was modified.")
print("Run deterministic tests:")
print("  /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra8_1_frozen_adapter_v0_1.py")
