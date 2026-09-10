from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
js = (PKG/"assets"/"biosafe_workflow_ui.js").read_text(encoding="utf-8")
css = (PKG/"assets"/"biosafe_workflow_ui.css").read_text(encoding="utf-8")

checks = [
    ("ask-workflow", 'Ask BioSafe' in js),
    ("review-workflow", 'Review a Document' in js),
    ("forme-workflow", 'Form E Assistant' in js),
    ("tablist-a11y", 'role", "tablist' in js or 'role","tablist' in js),
    ("aria-selected", "aria-selected" in js),
    ("loading-state", "biosafe-spinner" in js and "reviewing your request" in js),
    ("file-summary", "biosafe-file-summary" in js),
    ("forme-boundary-copy", "does not make an IBC determination" in js),
    ("focus-visible", "focus-visible" in css),
    ("mobile-tabs", "@media (max-width: 720px)" in css),
    ("no-api-rewrite", "fetch(" not in js and "XMLHttpRequest" not in js),
    ("public-api", "BioSafeWorkflowUI" in js),
]
failed = []
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
    if not ok:
        failed.append(name)

print(f"\nSummary: {len(checks)-len(failed)}/{len(checks)} passed")
if failed:
    raise SystemExit("Failures: " + ", ".join(failed))
print("Stage 10.2 workflow UI static regression: PASS")
