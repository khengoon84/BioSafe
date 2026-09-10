from pathlib import Path
import shutil

SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")
(TARGET/"src").mkdir(parents=True,exist_ok=True)
(TARGET/"tests").mkdir(parents=True,exist_ok=True)

for rel in [
    "src/interaction_manager_v0_1.py",
    "src/state_manager_v0_1.py",
    "src/reference_resolver_v0_1.py",
    "src/clarification_resolver_v0_1.py",
    "src/interaction_state_engine_v0_1.py",
    "tests/test_cra2_interaction_state_v0_1.py",
]:
    s=SRC/rel; d=TARGET/rel
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(s,d)

print("CRA-2 installed to:",TARGET)
print("CRA-1 contracts reused; no frozen Stage 8/9 files modified.")
print("Run:")
print("  /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/test_cra2_interaction_state_v0_1.py")
