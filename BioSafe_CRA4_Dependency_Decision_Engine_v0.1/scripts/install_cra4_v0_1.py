from pathlib import Path
import shutil

SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")
for sub in ["src","tests","config"]:
    (TARGET/sub).mkdir(parents=True,exist_ok=True)

for rel in [
    "src/dependency_decision_engine_v0_1.py",
    "config/decision_dependencies_v0_1.json",
    "tests/test_cra4_dependency_engine_v0_1.py",
]:
    s=SRC/rel; d=TARGET/rel
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(s,d)

print("CRA-4 installed to:",TARGET)
print("CRA-1/2/3 reused. No frozen Stage 8/9 files modified.")
print("Run:")
print("  /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra4_dependency_engine_v0_1.py")
