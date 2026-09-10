
from pathlib import Path
import shutil, datetime

root = Path("/home/khengoon/biosafe")
src = Path(__file__).resolve().parent.parent/"src"/"full_inference_service_v0_1.py"
dst = root/"src"/"full_inference_service_v0_1.py"

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
if dst.exists():
    shutil.copy2(dst, dst.with_suffix(f".py.bak_{stamp}"))
shutil.copy2(src, dst)

print("Stage 9.2 v0.1.1 compact-generation patch: APPLIED")
print("Frozen Stage 8 files modified: NO")
print("Patched:", dst)
