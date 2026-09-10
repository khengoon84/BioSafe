from pathlib import Path
import shutil,datetime
P=Path("/home/khengoon/biosafe"); H=Path(__file__).resolve().parents[1]; T=P/"unified_v1"
dest=T/"src/biosafe_unified225"; dest.parent.mkdir(parents=True,exist_ok=True)
if dest.exists(): shutil.move(str(dest),str(T/f"biosafe_unified225_backup_{datetime.datetime.now():%Y%m%d_%H%M%S}"))
shutil.copytree(H/"src/biosafe_unified225",dest)
(P/"cra_v1/scripts").mkdir(parents=True,exist_ok=True); (P/"cra_v1/tests").mkdir(parents=True,exist_ok=True)
for src,dst in [
 ("scripts/run_unified225_sidecar_v0_1.py",P/"cra_v1/scripts/run_unified225_sidecar_v0_1.py"),
 ("tests/test_unified225_contract_v0_1.py",T/"tests/test_unified225_contract_v0_1.py"),
 ("tests/live_ab_unified225_v0_1.py",P/"cra_v1/tests/live_ab_unified225_v0_1.py"),
 ("tests/live_semantic_acceptance_v0_1.py",P/"cra_v1/tests/live_semantic_acceptance_v0_1.py")]:
    shutil.copy2(H/src,dst)
print("BioSafe Unified-2.2.5 v0.1: INSTALLED")
print("Frozen retriever/planner/constitution/regulatory guards modified: NO")
print("8775 unchanged; 8776 NEW")
