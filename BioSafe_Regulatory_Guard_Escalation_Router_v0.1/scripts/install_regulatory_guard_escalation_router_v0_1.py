
from pathlib import Path
import argparse, shutil

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default="/home/khengoon/biosafe")
    a = ap.parse_args()
    here = Path(__file__).resolve().parent.parent
    root = Path(a.project_root).expanduser().resolve()
    (root/"src").mkdir(parents=True, exist_ok=True)
    (root/"scripts").mkdir(parents=True, exist_ok=True)
    (root/"data").mkdir(parents=True, exist_ok=True)

    for name in [
        "regulatory_language_guard_v0_1.py",
        "complexity_escalation_router_v0_1.py",
        "deployment_inference_policy_v0_1.py"
    ]:
        shutil.copy2(here/"src"/name, root/"src"/name)

    shutil.copy2(
        here/"tests"/"preflight_regulatory_guard_escalation_router_v0_1.py",
        root/"scripts"/"preflight_regulatory_guard_escalation_router_v0_1.py"
    )
    shutil.copy2(
        here/"data"/"Regulatory_Guard_Escalation_Router_v0.1_Manifest.json",
        root/"data"/"Regulatory_Guard_Escalation_Router_v0.1_Manifest.json"
    )
    print("BioSafe regulatory guard and escalation router copied into:", root)

if __name__ == "__main__":
    main()
