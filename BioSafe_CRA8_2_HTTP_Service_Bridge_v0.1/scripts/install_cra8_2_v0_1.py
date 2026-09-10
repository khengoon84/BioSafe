from pathlib import Path
import shutil
SRC=Path(__file__).resolve().parent.parent
TARGET=Path("/home/khengoon/biosafe/cra_v1")
for sub in ["src","tests","scripts"]:
    (TARGET/sub).mkdir(parents=True,exist_ok=True)
for rel in [
    "src/cra_service_runtime_v0_1.py",
    "src/cra_bridge_app_v0_1.py",
    "tests/test_cra8_2_service_runtime_v0_1.py",
    "tests/test_cra8_2_flask_http_contract_v0_1.py",
    "tests/test_cra8_2_http_contract_static_v0_1.py",
    "tests/live_http_smoke_cra8_2_v0_1.py",
    "scripts/run_cra8_2_sidecar_v0_1.py",
]:
    s=SRC/rel; d=TARGET/rel
    d.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(s,d)
print("CRA-8.2 installed to:",TARGET)
print("No frozen src/*.py and no existing browser/UI file was modified.")
