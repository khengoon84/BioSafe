
from pathlib import Path
import argparse, shutil

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    a = ap.parse_args()
    here = Path(__file__).resolve().parent.parent
    root = Path(a.project_root).expanduser().resolve()
    (root/"scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        here/"scripts"/"inspect_biosafe_pipeline_interface_v0_1.py",
        root/"scripts"/"inspect_biosafe_pipeline_interface_v0_1.py"
    )
    print("Pipeline interface inspector copied into:", root)

if __name__ == "__main__":
    main()
