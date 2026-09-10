
from pathlib import Path
import argparse, shutil
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",default="/home/khengoon/biosafe")
    a=ap.parse_args()
    root=Path(a.project_root).expanduser().resolve()
    here=Path(__file__).resolve().parent.parent
    (root/"src").mkdir(exist_ok=True)
    (root/"tests").mkdir(exist_ok=True)
    shutil.copy2(here/"src"/"integration_safety_gate_v0_1_1.py",
                 root/"src"/"integration_safety_gate_v0_1_1.py")
    shutil.copy2(here/"tests"/"regression_integration_safety_gate_v0_1_1.py",
                 root/"tests"/"regression_integration_safety_gate_v0_1_1.py")
    print("Safety Gate v0.1.1 copied into:",root)
if __name__=="__main__":
    main()
