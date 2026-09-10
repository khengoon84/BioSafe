
from pathlib import Path
import shutil, datetime

ROOT=Path("/home/khengoon/biosafe")
HERE=Path(__file__).resolve().parent.parent

src=HERE/"src"/"decision_quality_refinement_v0_1.py"
dst=ROOT/"src"/"decision_quality_refinement_v0_1.py"

if not dst.exists():
    raise SystemExit(
        "Existing Decision Quality Refinement integration not found. "
        "Apply v0.1.1 first."
    )

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=dst.with_suffix(f".py.bak_{stamp}")
shutil.copy2(dst,backup)
shutil.copy2(src,dst)

try:
    compile(dst.read_text(encoding="utf-8"),str(dst),"exec")
except Exception as e:
    shutil.copy2(backup,dst)
    raise SystemExit(f"Updated refinement failed syntax check; original restored: {e}")

print("BioSafe Decision Quality Refinement v0.1.2: INSTALLED")
print("Integration hooks changed: NO")
print("Frozen Stage 8 files modified: NO")
print("Updated:",dst)
print("Backup:",backup)
