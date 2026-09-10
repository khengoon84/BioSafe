from pathlib import Path
p=Path(__file__).resolve().parent.parent/"tests"/"run_cra8_3_full_corrected_regression_v0_2.py"
text=p.read_text(encoding="utf-8")
compile(text,str(p),"exec")
checks={
    "targets corrected sidecar":"http://127.0.0.1:8767" in text,
    "12 cases":all(f'"C{i:02d}"' in text for i in range(1,13)),
    "follow-up repaired assertion":"continuity_repaired" in text,
    "review Form E suppression":"no_form_e_output" in text,
    "review LMO suppression":"no_lmo_output" in text,
    "Form E recommendation grounding":"no_unsupported_lab_director" in text and "no_unsupported_clearance" in text,
    "report path":"cra8_3_full_corrected_regression_report_v0_2.json" in text,
}
for k,v in checks.items():
    print(("PASS" if v else "FAIL"),k)
print(f"\nSummary: {sum(checks.values())}/{len(checks)} passed")
if not all(checks.values()):
    raise SystemExit(1)
print("CRA-8.3 full corrected package preflight: PASS")
