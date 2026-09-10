
from pathlib import Path
import argparse, shutil

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    a=ap.parse_args()
    root=Path(a.project_root).resolve()
    src=Path(__file__).resolve().parent.parent

    target=root/"stage9_local_shell"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(src/"app", target/"app")
    shutil.copy2(src/"requirements.txt", target/"requirements.txt")

    print("Stage 9 local shell copied to:", target)
    print("Next:")
    print(f"  cd {target}")
    print("  ../.venv/bin/pip install -r requirements.txt")
    print("  ../.venv/bin/python app/main.py")

if __name__=="__main__":
    main()
