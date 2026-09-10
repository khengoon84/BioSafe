
from pathlib import Path
import argparse, shutil
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",default="/home/khengoon/biosafe")
    a=ap.parse_args()
    here=Path(__file__).resolve().parent.parent
    root=Path(a.project_root).expanduser().resolve()
    for d in ("data","scripts"):
        (root/d).mkdir(parents=True,exist_ok=True)
    for name in [
        "deployment_readiness_cases_v0.1.json",
        "deployment_readiness_document_fixtures_v0.1.json"
    ]:
        shutil.copy2(here/"data"/name,root/"data"/name)
    for name in [
        "run_deployment_readiness_live24_v0_4_fullfrozenstack.py",
        "preflight_deployment_readiness_live24_v0_4_fullfrozenstack.py"
    ]:
        shutil.copy2(here/"scripts"/name,root/"scripts"/name)
    print("Live24 v0.4 Full Frozen Stack harness copied into:",root)
if __name__=="__main__": main()
