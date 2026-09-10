
from pathlib import Path
import argparse, shutil

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    a=ap.parse_args()
    root=Path(a.project_root).resolve()
    here=Path(__file__).resolve().parent.parent

    (root/"src").mkdir(exist_ok=True)
    (root/"tests").mkdir(exist_ok=True)

    shutil.copy2(here/"src"/"policy_decision_guard_v0_3_3.py",
                 root/"src"/"policy_decision_guard_v0_3_3.py")
    shutil.copy2(here/"tests"/"regression_policy_decision_guard_v0_3_3.py",
                 root/"tests"/"regression_policy_decision_guard_v0_3_3.py")
    print("Policy & Decision Guard v0.3.3 copied into:", root)

if __name__=="__main__":
    main()
