
from pathlib import Path
import argparse,shutil
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--project-root",default="/home/khengoon/biosafe")
    a=ap.parse_args(); root=Path(a.project_root).resolve()
    here=Path(__file__).resolve().parent.parent
    (root/"scripts").mkdir(parents=True,exist_ok=True)
    shutil.copy2(here/"scripts"/"inspect_final_frozen_stack_interfaces_v0_3.py",root/"scripts"/"inspect_final_frozen_stack_interfaces_v0_3.py")
    print("Inspector copied into:",root)
if __name__=="__main__":main()
