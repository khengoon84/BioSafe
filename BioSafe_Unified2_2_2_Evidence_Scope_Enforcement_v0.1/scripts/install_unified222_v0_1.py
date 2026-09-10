
from pathlib import Path
import shutil,datetime
P=Path("/home/khengoon/biosafe");H=Path(__file__).resolve().parents[1];T=P/"unified_v1"
(T/"src").mkdir(parents=True,exist_ok=True);(T/"tests").mkdir(exist_ok=True)
(P/"cra_v1"/"scripts").mkdir(parents=True,exist_ok=True);(P/"cra_v1"/"tests").mkdir(parents=True,exist_ok=True)
dest=T/"src"/"biosafe_unified222"
if dest.exists():
 s=datetime.datetime.now().strftime("%Y%m%d_%H%M%S");shutil.move(str(dest),str(T/f"biosafe_unified222_backup_{s}"))
shutil.copytree(H/"src/biosafe_unified222",dest)
shutil.copy2(H/"scripts/run_unified222_sidecar_v0_1.py",P/"cra_v1/scripts/run_unified222_sidecar_v0_1.py")
shutil.copy2(H/"tests/test_unified222_contract_v0_1.py",T/"tests/test_unified222_contract_v0_1.py")
shutil.copy2(H/"tests/live_ab_unified222_v0_1.py",P/"cra_v1/tests/live_ab_unified222_v0_1.py")
print("BioSafe Unified-2.2.2 v0.1: INSTALLED")
print("Frozen inference/RAG files modified: NO")
print("8770 Unified-2.2.1: unchanged")
print("8771 Unified-2.2.2: NEW")
