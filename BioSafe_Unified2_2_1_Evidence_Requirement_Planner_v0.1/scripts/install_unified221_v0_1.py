
from pathlib import Path
import shutil,datetime
PROJECT=Path("/home/khengoon/biosafe"); HERE=Path(__file__).resolve().parents[1]; TARGET=PROJECT/"unified_v1"
if not PROJECT.exists(): raise SystemExit(f"Project not found: {PROJECT}")
(TARGET/"src").mkdir(parents=True,exist_ok=True); (TARGET/"tests").mkdir(exist_ok=True)
(PROJECT/"cra_v1"/"scripts").mkdir(parents=True,exist_ok=True); (PROJECT/"cra_v1"/"tests").mkdir(parents=True,exist_ok=True)
dest=TARGET/"src"/"biosafe_unified221"
if dest.exists():
    stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.move(str(dest),str(TARGET/f"biosafe_unified221_backup_{stamp}"))
shutil.copytree(HERE/"src"/"biosafe_unified221",dest)
shutil.copy2(HERE/"scripts"/"run_unified221_sidecar_v0_1.py",PROJECT/"cra_v1"/"scripts"/"run_unified221_sidecar_v0_1.py")
shutil.copy2(HERE/"tests"/"test_evidence_planner_v0_1.py",TARGET/"tests"/"test_evidence_planner_v0_1.py")
shutil.copy2(HERE/"tests"/"live_ab_unified221_v0_1.py",PROJECT/"cra_v1"/"tests"/"live_ab_unified221_v0_1.py")
print("BioSafe Unified-2.2.1 Evidence Requirement Planner v0.1: INSTALLED")
print("Frozen inference/RAG files modified: NO")
print("8768 baseline: unchanged")
print("8769 Unified-2.2 experiment: unchanged")
print("8770 Unified-2.2.1 experiment: NEW")
