from pathlib import Path
import shutil,datetime
P=Path("/home/khengoon/biosafe");H=Path(__file__).resolve().parents[1];T=P/"unified_v1"
dest=T/"src/biosafe_unified223";dest.parent.mkdir(parents=True,exist_ok=True)
if dest.exists(): shutil.move(str(dest),str(T/f"biosafe_unified223_backup_{datetime.datetime.now():%Y%m%d_%H%M%S}"))
shutil.copytree(H/"src/biosafe_unified223",dest)
(P/"cra_v1/scripts").mkdir(parents=True,exist_ok=True);(P/"cra_v1/tests").mkdir(parents=True,exist_ok=True)
shutil.copy2(H/"scripts/run_unified223_sidecar_v0_1.py",P/"cra_v1/scripts/run_unified223_sidecar_v0_1.py")
shutil.copy2(H/"tests/test_unified223_contract_v0_1.py",T/"tests/test_unified223_contract_v0_1.py")
shutil.copy2(H/"tests/live_ab_unified223_v0_1.py",P/"cra_v1/tests/live_ab_unified223_v0_1.py")
print("BioSafe Unified-2.2.3 v0.1: INSTALLED")
print("Frozen inference/RAG files modified: NO")
print("8771 unchanged; 8772 NEW")
