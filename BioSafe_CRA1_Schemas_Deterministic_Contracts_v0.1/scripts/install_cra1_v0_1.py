from pathlib import Path
import shutil, datetime

SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")
TARGET.mkdir(parents=True,exist_ok=True)
(TARGET/"src").mkdir(exist_ok=True)
(TARGET/"tests").mkdir(exist_ok=True)
(TARGET/"examples").mkdir(exist_ok=True)

for rel in [
    "src/cra_contracts_v0_1.py",
    "src/cra_contract_validators_v0_1.py",
    "tests/test_cra1_contracts_v0_1.py",
    "examples/example_contract_objects_v0_1.py",
]:
    s=SRC/rel
    d=TARGET/rel
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(s,d)

print("CRA-1 installed to:",TARGET)
print("No frozen Stage 8/9 files modified.")
print("Run:")
print("  /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra1_contracts_v0_1.py")
