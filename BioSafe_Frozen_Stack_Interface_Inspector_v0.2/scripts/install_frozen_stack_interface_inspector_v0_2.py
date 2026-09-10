
from pathlib import Path
import argparse,shutil
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",default="/home/khengoon/biosafe")
    a=ap.parse_args()
    here=Path(__file__).resolve().parent.parent
    root=Path(a.project_root).expanduser().resolve()
    (root/"scripts").mkdir(parents=True,exist_ok=True)
    shutil.copy2(here/"scripts"/"inspect_frozen_stack_interfaces_v0_2.py",
                 root/"scripts"/"inspect_frozen_stack_interfaces_v0_2.py")
    print("Frozen stack interface inspector copied into:",root)
if __name__=="__main__":
    main()
