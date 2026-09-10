
from pathlib import Path
import shutil, datetime
PROJECT=Path("/home/khengoon/biosafe")
HERE=Path(__file__).resolve().parents[1]
TARGET=PROJECT/"unified_v1"
if not PROJECT.exists(): raise SystemExit(f"BioSafe project not found: {PROJECT}")

(TARGET/"src").mkdir(parents=True,exist_ok=True)
(TARGET/"config").mkdir(exist_ok=True)
(TARGET/"tests").mkdir(exist_ok=True)
(PROJECT/"cra_v1"/"scripts").mkdir(parents=True,exist_ok=True)
(PROJECT/"cra_v1"/"tests").mkdir(parents=True,exist_ok=True)

dest=TARGET/"src"/"biosafe_unified22"
if dest.exists():
    stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.move(str(dest),str(TARGET/f"biosafe_unified22_backup_{stamp}"))
shutil.copytree(HERE/"src"/"biosafe_unified22",dest)

shutil.copy2(HERE/"config"/"behavioral_constitution_v1_0.txt",TARGET/"config"/"behavioral_constitution_v1_0.txt")
shutil.copy2(HERE/"scripts"/"run_unified22_sidecar_v0_1.py",PROJECT/"cra_v1"/"scripts"/"run_unified22_sidecar_v0_1.py")
shutil.copy2(HERE/"tests"/"test_unified22_message_contract_v0_1.py",TARGET/"tests"/"test_unified22_message_contract_v0_1.py")
shutil.copy2(HERE/"tests"/"live_ab_unified22_v0_1.py",PROJECT/"cra_v1"/"tests"/"live_ab_unified22_v0_1.py")

print("BioSafe Unified-2.2 Constitution-Aware Generation v0.1: INSTALLED")
print("Frozen inference/RAG files modified: NO")
print("Existing 8768 Unified-2.1 sidecar modified: NO")
print("Experimental Unified-2.2 sidecar: 8769")
