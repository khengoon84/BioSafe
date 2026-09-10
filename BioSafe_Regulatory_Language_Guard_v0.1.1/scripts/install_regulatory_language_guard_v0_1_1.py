
from pathlib import Path
import argparse, shutil

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    a=ap.parse_args()
    here=Path(__file__).resolve().parent.parent
    root=Path(a.project_root).expanduser().resolve()
    for d in ("src","scripts","data"):
        (root/d).mkdir(parents=True, exist_ok=True)

    shutil.copy2(here/"src"/"regulatory_language_guard_v0_1.py", root/"src"/"regulatory_language_guard_v0_1.py")
    for name in [
        "run_regulatory_language_guard_semantic_regression_v0_1_1.py",
        "run_regulatory_guard_escalation_regression_v0_1.py",
        "run_deployment_inference_e2e_regression_v0_1.py",
    ]:
        shutil.copy2(here/"scripts"/name, root/"scripts"/name)
    shutil.copy2(here/"tests"/"preflight_regulatory_language_guard_v0_1_1.py",
                 root/"scripts"/"preflight_regulatory_language_guard_v0_1_1.py")
    for name in [
        "regulatory_language_guard_semantic_regression_v0.1.1.json",
        "regulatory_guard_escalation_regression_v0.1.json",
        "deployment_inference_e2e_regression_v0.1.json",
    ]:
        shutil.copy2(here/"data"/name, root/"data"/name)

    print("Regulatory Language Guard v0.1.1 copied into:", root)
    print("Escalation Router v0.1 unchanged.")

if __name__=="__main__":
    main()
