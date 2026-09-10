from pathlib import Path
import shutil, datetime

ROOT=Path("/home/khengoon/biosafe")
HERE=Path(__file__).resolve().parent.parent
shutil.copy2(HERE/"src"/"regulatory_applicability_guard_v0_1.py", ROOT/"src"/"regulatory_applicability_guard_v0_1.py")

svc=ROOT/"src"/"full_inference_service_v0_1.py"
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
shutil.copy2(svc, svc.with_suffix(f".py.bak_{stamp}"))
s=svc.read_text(encoding="utf-8")

imp='from regulatory_language_guard_v0_1 import RegulatoryLanguageGuardV011\\n'
addimp='from regulatory_applicability_guard_v0_1 import RegulatoryApplicabilityGuardV01\\n'
if addimp.strip() not in s:
    s=s.replace(imp, imp+addimp)

init='        self.reg_guard = RegulatoryLanguageGuardV011()\\n'
addin='        self.applicability_guard = RegulatoryApplicabilityGuardV01()\\n'
if addin.strip() not in s:
    s=s.replace(init, init+addin)

needle='        final, _ = self.reg_guard.apply(final, bundle.get("evidence_bundle", []))\\n\\n'
insert=(
    '        final, _ = self.reg_guard.apply(final, bundle.get("evidence_bundle", []))\\n\\n'
    '        applicability = self.applicability_guard.apply(\\n'
    '            final,\\n'
    '            user_query=query,\\n'
    '            document_text="\\\\n\\\\n".join((d.get("text") or "") for d in documents),\\n'
    '            structured_packet=packet,\\n'
    '        )\\n'
    '        final = applicability.response\\n\\n'
)
if "applicability = self.applicability_guard.apply(" not in s:
    if needle not in s:
        raise SystemExit("Insertion point not found; no patch applied.")
    s=s.replace(needle, insert)

svc.write_text(s,encoding="utf-8")
print("Regulatory Applicability Guard v0.1: INSTALLED")
print("Frozen Stage 8 files modified: NO")
print("Stage 9 integration adapter patched:", svc)
