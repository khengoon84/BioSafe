
from pathlib import Path
import argparse, shutil, datetime

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    a=ap.parse_args()
    root=Path(a.project_root).resolve()
    here=Path(__file__).resolve().parent.parent
    shell=root/"stage9_local_shell"

    if not shell.exists():
        raise SystemExit(f"Stage 9 shell not found: {shell}")

    (root/"src").mkdir(exist_ok=True)
    shutil.copy2(here/"src"/"full_inference_service_v0_1.py",
                 root/"src"/"full_inference_service_v0_1.py")

    stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for name in ("service.py","main.py"):
        old=shell/"app"/name
        if old.exists():
            shutil.copy2(old, old.with_suffix(f".py.bak_{stamp}"))

    shutil.copy2(here/"src"/"stage9_service_replacement.py", shell/"app"/"service.py")
    shutil.copy2(here/"src"/"stage9_main_replacement.py", shell/"app"/"main.py")

    print("Stage 9.2 Full Inference Integration copied successfully.")
    print("Frozen Stage 8 modules were not overwritten.")
    print("Shell:", shell)

if __name__=="__main__":
    main()
