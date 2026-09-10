from pathlib import Path
import json

PKG = Path(__file__).resolve().parent.parent
js = (PKG/"assets"/"biosafe_response_renderer.js").read_text(encoding="utf-8")
css = (PKG/"assets"/"biosafe_response_renderer.css").read_text(encoding="utf-8")
fixture = json.loads((PKG/"fixtures"/"sample_biosafe_response.json").read_text(encoding="utf-8"))

checks = [
    ("renderer-api","BioSafeResponseRenderer" in js),
    ("mutation-observer","MutationObserver" in js),
    ("raw-json-debug","Developer details" in js and "Copy raw JSON" in js),
    ("conclusion-section",">Conclusion<" in js),
    ("authority-section",">Applicable authority<" in js),
    ("evidence-section",">Evidence<" in js),
    ("missing-section",">Information needed<" in js),
    ("next-step-section",">Recommended next steps<" in js),
    ("limitations-section",">Limitations<" in js),
    ("safety-section",">Safety & response status<" in js),
    ("responsive-css","@media (max-width:680px)" in css),
    ("fixture-shape",isinstance(fixture.get("evidence"),list) and isinstance(fixture.get("missing_information"),list)),
]
failed=[]
for name,ok in checks:
    print(("PASS" if ok else "FAIL"),name)
    if not ok: failed.append(name)
print(f"\nSummary: {len(checks)-len(failed)}/{len(checks)} passed")
if failed:
    raise SystemExit("Failures: "+", ".join(failed))
print("Stage 10.1 response-presentation static regression: PASS")
