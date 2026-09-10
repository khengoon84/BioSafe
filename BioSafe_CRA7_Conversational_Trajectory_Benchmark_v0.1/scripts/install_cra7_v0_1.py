from pathlib import Path
import shutil

SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")
for sub in ["src","tests","benchmarks","reports"]:
    (TARGET/sub).mkdir(parents=True,exist_ok=True)

for rel in [
    "src/trajectory_harness_v0_1.py",
    "benchmarks/trajectory_cases_v0_1.json",
    "tests/run_cra7_trajectory_benchmark_v0_1.py",
]:
    s=SRC/rel; d=TARGET/rel
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(s,d)

print("CRA-7 installed to:",TARGET)
print("CRA-1..6 reused. No live UI or frozen Stage 8/9 component modified.")
print("Run:")
print("  /home/khengoon/biosafe/.venv/bin/python /home/khengoon/biosafe/cra_v1/tests/run_cra7_trajectory_benchmark_v0_1.py")
