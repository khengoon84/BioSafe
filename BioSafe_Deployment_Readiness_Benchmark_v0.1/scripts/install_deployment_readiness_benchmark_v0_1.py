
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
    shutil.copy2(here/"data"/"deployment_readiness_cases_v0.1.json",root/"data"/"deployment_readiness_cases_v0.1.json")
    shutil.copy2(here/"scripts"/"run_deployment_readiness_routing_gate_v0_1.py",root/"scripts"/"run_deployment_readiness_routing_gate_v0_1.py")
    shutil.copy2(here/"tests"/"preflight_deployment_readiness_benchmark_v0_1.py",root/"scripts"/"preflight_deployment_readiness_benchmark_v0_1.py")
    print("Deployment Readiness Benchmark v0.1 copied into:",root)
if __name__=="__main__":
    main()
