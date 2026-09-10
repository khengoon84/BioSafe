from pathlib import Path
import shutil
SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")
for sub in ["src","tests","scripts","fixtures","reports"]:
    (TARGET/sub).mkdir(parents=True,exist_ok=True)

for rel in [
    "src/followup_continuity_guard_v0_1.py",
    "src/integration_quality_guard_v0_1.py",
    "src/cra_service_runtime_v0_1_1.py",
    "src/cra_bridge_app_v0_1_1.py",
    "tests/test_cra8_3_1_quality_guards_v0_1.py",
    "tests/run_cra8_3_1_live_regression_v0_1.py",
    "scripts/run_cra8_3_1_sidecar_v0_1.py",
    "fixtures/sample_review_sop.txt",
]:
    s=SRC/rel
    d=TARGET/rel
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(s,d)

print("CRA-8.3.1 installed to:",TARGET)
print("No frozen Stage 8/9 inference file was modified.")
print("CRA-8.2 sidecar on 8766 and existing UI on 8765 remain untouched.")
