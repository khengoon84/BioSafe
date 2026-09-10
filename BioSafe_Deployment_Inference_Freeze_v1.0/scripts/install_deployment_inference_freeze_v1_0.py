
from pathlib import Path
import argparse, shutil

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    a = ap.parse_args()
    here = Path(__file__).resolve().parent.parent
    root = Path(a.project_root).expanduser().resolve()

    for d in ("data","docs","scripts"):
        (root/d).mkdir(parents=True, exist_ok=True)

    shutil.copy2(
        here/"data"/"BioSafe_Deployment_Inference_Layer_v1.0_FREEZE.json",
        root/"data"/"BioSafe_Deployment_Inference_Layer_v1.0_FREEZE.json"
    )
    shutil.copy2(
        here/"data"/"BioSafe_Deployment_Readiness_Benchmark_v0.1.json",
        root/"data"/"BioSafe_Deployment_Readiness_Benchmark_v0.1.json"
    )
    shutil.copy2(
        here/"docs"/"ARCHITECTURE_FREEZE.md",
        root/"docs"/"ARCHITECTURE_FREEZE.md"
    )
    shutil.copy2(
        here/"tests"/"verify_deployment_inference_freeze_v1_0.py",
        root/"scripts"/"verify_deployment_inference_freeze_v1_0.py"
    )

    print("BioSafe Deployment Inference freeze files copied into:", root)

if __name__ == "__main__":
    main()
