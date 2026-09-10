from pathlib import Path
import shutil, datetime
PROJECT=Path("/home/khengoon/biosafe"); TARGET=PROJECT/"unified_v1"; HERE=Path(__file__).resolve().parents[1]
if not PROJECT.exists(): raise SystemExit(f"BioSafe project not found: {PROJECT}")
(TARGET/"src").mkdir(parents=True,exist_ok=True); (TARGET/"config").mkdir(exist_ok=True); (TARGET/"tests").mkdir(exist_ok=True); (PROJECT/"cra_v1"/"scripts").mkdir(parents=True,exist_ok=True); (PROJECT/"cra_v1"/"tests").mkdir(parents=True,exist_ok=True)
dest=TARGET/"src"/"biosafe_unified2"
if dest.exists():
    stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"); shutil.move(str(dest),str(TARGET/f"biosafe_unified2_backup_{stamp}"))
shutil.copytree(HERE/"src"/"biosafe_unified2",dest); shutil.copy2(HERE/"config"/"behavioral_constitution_v1_0.txt",TARGET/"config"/"behavioral_constitution_v1_0.txt"); shutil.copy2(HERE/"tests"/"test_unified2_contract_v0_1.py",TARGET/"tests"/"test_unified2_contract_v0_1.py"); shutil.copy2(HERE/"scripts"/"run_unified2_sidecar_v0_1.py",PROJECT/"cra_v1"/"scripts"/"run_unified2_sidecar_v0_1.py"); shutil.copy2(HERE/"tests"/"live_smoke_unified2_v0_1.py",PROJECT/"cra_v1"/"tests"/"live_smoke_unified2_v0_1.py")
print("BioSafe Unified-2 Orchestration Integration v0.1: INSTALLED"); print("Frozen inference/RAG modified: NO"); print("Existing 8765 UI modified: NO"); print("Existing 8767 CRA sidecar modified: NO"); print("Experimental Unified-2 sidecar port: 8768"); print(f"Installed root: {TARGET}")
