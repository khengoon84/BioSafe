
from pathlib import Path
import argparse, shutil

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    a = ap.parse_args()
    here = Path(__file__).resolve().parent.parent
    root = Path(a.project_root).expanduser().resolve()

    for d in ("src","scripts","data"):
        (root/d).mkdir(parents=True, exist_ok=True)

    for name in [
        "regulatory_language_guard_v0_1.py",
        "complexity_escalation_router_v0_1.py",
        "deployment_inference_policy_v0_1.py",
        "deployment_inference_integration_v0_1.py",
    ]:
        shutil.copy2(here/"src"/name, root/"src"/name)

    shutil.copy2(
        here/"scripts"/"run_deployment_inference_e2e_regression_v0_1.py",
        root/"scripts"/"run_deployment_inference_e2e_regression_v0_1.py"
    )
    shutil.copy2(
        here/"tests"/"preflight_deployment_inference_integration_v0_1.py",
        root/"scripts"/"preflight_deployment_inference_integration_v0_1.py"
    )
    shutil.copy2(
        here/"data"/"deployment_inference_e2e_regression_v0.1.json",
        root/"data"/"deployment_inference_e2e_regression_v0.1.json"
    )
    print("Deployment inference integration files copied into:", root)

if __name__ == "__main__":
    main()
