
from pathlib import Path
import shutil
import datetime
import re

ROOT = Path("/home/khengoon/biosafe")
HERE = Path(__file__).resolve().parent.parent

guard_src = HERE/"src"/"regulatory_applicability_guard_v0_1.py"
guard_dst = ROOT/"src"/"regulatory_applicability_guard_v0_1.py"
shutil.copy2(guard_src, guard_dst)

svc = ROOT/"src"/"full_inference_service_v0_1.py"
if not svc.exists():
    raise SystemExit(f"Missing integration adapter: {svc}")

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = svc.with_suffix(f".py.bak_{stamp}")
shutil.copy2(svc, backup)

s = svc.read_text(encoding="utf-8")
original = s

# 1) Import
import_stmt = "from regulatory_applicability_guard_v0_1 import RegulatoryApplicabilityGuardV01"
if import_stmt not in s:
    # Prefer insertion after the existing regulatory language guard import.
    m = re.search(
        r'^(from\s+regulatory_language_guard_v0_1\s+import\s+RegulatoryLanguageGuardV011\s*)$',
        s, re.M
    )
    if m:
        s = s[:m.end()] + "\n" + import_stmt + s[m.end():]
    else:
        # Fallback: insert before first class definition.
        m = re.search(r'^class\s+', s, re.M)
        if not m:
            shutil.copy2(backup, svc)
            raise SystemExit("Could not locate a safe import insertion point; original restored.")
        s = s[:m.start()] + import_stmt + "\n\n" + s[m.start():]

# 2) Constructor
init_stmt = "        self.applicability_guard = RegulatoryApplicabilityGuardV01()"
if "self.applicability_guard = RegulatoryApplicabilityGuardV01()" not in s:
    # Insert after self.reg_guard assignment, allowing spacing variations.
    m = re.search(
        r'^(?P<indent>\s*)self\.reg_guard\s*=\s*RegulatoryLanguageGuardV011\(\)\s*$',
        s, re.M
    )
    if not m:
        shutil.copy2(backup, svc)
        raise SystemExit("Could not locate self.reg_guard constructor line; original restored.")
    insert_at = m.end()
    indent = m.group("indent")
    s = s[:insert_at] + "\n" + indent + "self.applicability_guard = RegulatoryApplicabilityGuardV01()" + s[insert_at:]

# 3) Apply guard after Regulatory Language Guard.
if "applicability = self.applicability_guard.apply(" not in s:
    # Match the actual call regardless of whether it is assigned as tuple or intermediate variable.
    patterns = [
        r'^(?P<indent>\s*)final\s*,\s*_\s*=\s*self\.reg_guard\.apply\([^\n]*\)\s*$',
        r'^(?P<indent>\s*)final\s*=\s*self\.reg_guard\.apply\([^\n]*\)\s*$',
    ]
    m = None
    for pat in patterns:
        m = re.search(pat, s, re.M)
        if m:
            break

    if not m:
        # More permissive fallback: find any single line containing self.reg_guard.apply(...)
        m = re.search(r'^(?P<indent>\s*).*self\.reg_guard\.apply\([^\n]*\).*$',
                      s, re.M)

    if not m:
        shutil.copy2(backup, svc)
        raise SystemExit(
            "Could not locate Regulatory Language Guard application line. "
            "Original integration adapter restored."
        )

    indent = m.group("indent")
    block = (
        "\n\n"
        + indent + "applicability = self.applicability_guard.apply(\n"
        + indent + "    final,\n"
        + indent + "    user_query=query,\n"
        + indent + '    document_text="\\n\\n".join((d.get("text") or "") for d in documents),\n'
        + indent + "    structured_packet=packet,\n"
        + indent + ")\n"
        + indent + "final = applicability.response"
    )
    s = s[:m.end()] + block + s[m.end():]

if s == original:
    print("Regulatory Applicability Guard v0.1.1: already installed; no changes needed.")
else:
    svc.write_text(s, encoding="utf-8")

# Syntax-check patched adapter. Restore if invalid.
try:
    compile(svc.read_text(encoding="utf-8"), str(svc), "exec")
except Exception as e:
    shutil.copy2(backup, svc)
    raise SystemExit(f"Patched file failed syntax check; original restored. Error: {e}")

print("Regulatory Applicability Guard v0.1.1: INSTALLED")
print("Frozen Stage 8 files modified: NO")
print("Patched:", svc)
print("Backup:", backup)
