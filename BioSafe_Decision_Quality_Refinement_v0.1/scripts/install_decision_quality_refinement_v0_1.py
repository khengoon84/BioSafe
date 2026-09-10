
from pathlib import Path
import shutil, datetime, re

ROOT=Path("/home/khengoon/biosafe")
HERE=Path(__file__).resolve().parent.parent

src=HERE/"src"/"decision_quality_refinement_v0_1.py"
dst=ROOT/"src"/"decision_quality_refinement_v0_1.py"
shutil.copy2(src,dst)

svc=ROOT/"src"/"full_inference_service_v0_1.py"
if not svc.exists():
    raise SystemExit(f"Missing integration adapter: {svc}")

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=svc.with_suffix(f".py.bak_{stamp}")
shutil.copy2(svc,backup)

s=svc.read_text(encoding="utf-8")
original=s

imp="from decision_quality_refinement_v0_1 import BioSafeDecisionQualityRefinementV01"
if imp not in s:
    # Prefer after applicability guard import.
    m=re.search(r'^(from\\s+regulatory_applicability_guard_v0_1\\s+import\\s+RegulatoryApplicabilityGuardV01\\s*)$',s,re.M)
    if m:
        s=s[:m.end()]+"\\n"+imp+s[m.end():]
    else:
        m=re.search(r'^class\\s+',s,re.M)
        if not m:
            shutil.copy2(backup,svc)
            raise SystemExit("No safe import insertion point; original restored.")
        s=s[:m.start()]+imp+"\\n\\n"+s[m.start():]

if "self.decision_quality_refinement = BioSafeDecisionQualityRefinementV01()" not in s:
    m=re.search(r'^(?P<indent>\\s*)self\\.applicability_guard\\s*=\\s*RegulatoryApplicabilityGuardV01\\(\\)\\s*$',s,re.M)
    if not m:
        shutil.copy2(backup,svc)
        raise SystemExit("Applicability guard constructor not found; original restored.")
    indent=m.group("indent")
    s=s[:m.end()]+"\\n"+indent+"self.decision_quality_refinement = BioSafeDecisionQualityRefinementV01()"+s[m.end():]

if "quality = self.decision_quality_refinement.apply(" not in s:
    # Insert after final = applicability.response
    m=re.search(r'^(?P<indent>\\s*)final\\s*=\\s*applicability\\.response\\s*$',s,re.M)
    if not m:
        shutil.copy2(backup,svc)
        raise SystemExit("Applicability integration point not found; original restored.")
    indent=m.group("indent")
    block=(
        "\\n\\n"+indent+"quality = self.decision_quality_refinement.apply(\\n"
        +indent+"    final,\\n"
        +indent+"    user_query=query,\\n"
        +indent+'    document_text="\\\\n\\\\n".join((d.get("text") or "") for d in documents),\\n'
        +indent+"    structured_packet=packet,\\n"
        +indent+")\\n"
        +indent+"final = quality.response"
    )
    s=s[:m.end()]+block+s[m.end():]

svc.write_text(s,encoding="utf-8")
try:
    compile(svc.read_text(encoding="utf-8"),str(svc),"exec")
except Exception as e:
    shutil.copy2(backup,svc)
    raise SystemExit(f"Patch syntax check failed; original restored: {e}")

print("BioSafe Decision Quality Refinement v0.1: INSTALLED")
print("Frozen Stage 8 files modified: NO")
print("Patched:",svc)
print("Backup:",backup)
