
from pathlib import Path
import shutil, datetime

ROOT = Path("/home/khengoon/biosafe")
HERE = Path(__file__).resolve().parent.parent

guard_src = HERE/"src"/"decision_quality_refinement_v0_1.py"
guard_dst = ROOT/"src"/"decision_quality_refinement_v0_1.py"
shutil.copy2(guard_src, guard_dst)

svc = ROOT/"src"/"full_inference_service_v0_1.py"
if not svc.exists():
    raise SystemExit(f"Missing integration adapter: {svc}")

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = svc.with_suffix(f".py.bak_{stamp}")
shutil.copy2(svc, backup)

s = svc.read_text(encoding="utf-8")
original = s

# 1. Import: insert directly after the existing applicability-guard import.
import_anchor = "from regulatory_applicability_guard_v0_1 import RegulatoryApplicabilityGuardV01\n"
import_stmt = "from decision_quality_refinement_v0_1 import BioSafeDecisionQualityRefinementV01\n"
if import_stmt not in s:
    if import_anchor not in s:
        shutil.copy2(backup, svc)
        raise SystemExit("Applicability-guard import anchor not found; original restored.")
    s = s.replace(import_anchor, import_anchor + import_stmt, 1)

# 2. Constructor: insert directly after the existing applicability-guard constructor.
ctor_anchor = "        self.applicability_guard = RegulatoryApplicabilityGuardV01()\n"
ctor_stmt = "        self.decision_quality_refinement = BioSafeDecisionQualityRefinementV01()\n"
if ctor_stmt not in s:
    if ctor_anchor not in s:
        shutil.copy2(backup, svc)
        raise SystemExit("Applicability-guard constructor anchor not found; original restored.")
    s = s.replace(ctor_anchor, ctor_anchor + ctor_stmt, 1)

# 3. Application: insert immediately after 'final = applicability.response'.
apply_anchor = "        final = applicability.response\n"
apply_block = (
    "\n"
    "        quality = self.decision_quality_refinement.apply(\n"
    "            final,\n"
    "            user_query=query,\n"
    '            document_text="\\n\\n".join((d.get("text") or "") for d in documents),\n'
    "            structured_packet=packet,\n"
    "        )\n"
    "        final = quality.response\n"
)
if "quality = self.decision_quality_refinement.apply(" not in s:
    if apply_anchor not in s:
        shutil.copy2(backup, svc)
        raise SystemExit("Applicability-result anchor not found; original restored.")
    s = s.replace(apply_anchor, apply_anchor + apply_block, 1)

svc.write_text(s, encoding="utf-8")

# Syntax-check the patched adapter. Restore automatically on failure.
try:
    compile(svc.read_text(encoding="utf-8"), str(svc), "exec")
except Exception as e:
    shutil.copy2(backup, svc)
    raise SystemExit(f"Patched adapter failed syntax check; original restored. Error: {e}")

print("BioSafe Decision Quality Refinement v0.1.1: INSTALLED")
print("Frozen Stage 8 files modified: NO")
print("Patched:", svc)
print("Backup:", backup)
