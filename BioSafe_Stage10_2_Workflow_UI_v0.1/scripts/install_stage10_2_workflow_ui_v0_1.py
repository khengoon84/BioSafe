from pathlib import Path
import shutil, datetime

ROOT = Path("/home/khengoon/biosafe/stage9_local_shell")
HERE = Path(__file__).resolve().parent.parent

if not ROOT.exists():
    raise SystemExit(f"BioSafe shell not found: {ROOT}")

template_candidates = [
    ROOT/"app"/"templates"/"index.html",
    ROOT/"templates"/"index.html",
]
static_candidates = [
    ROOT/"app"/"static",
    ROOT/"static",
]

template = next((p for p in template_candidates if p.exists()), None)
static_dir = next((p for p in static_candidates if p.exists()), None)

if template is None:
    raise SystemExit("Could not locate index.html. No files changed.")

if static_dir is None:
    static_dir = ROOT/"app"/"static" if (ROOT/"app").exists() else ROOT/"static"
    static_dir.mkdir(parents=True, exist_ok=True)

assets_dir = static_dir/"biosafe_stage10"
assets_dir.mkdir(parents=True, exist_ok=True)

for name in ["biosafe_workflow_ui.css","biosafe_workflow_ui.js"]:
    shutil.copy2(HERE/"assets"/name, assets_dir/name)

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup = template.with_suffix(f".html.bak_stage10_2_{stamp}")
shutil.copy2(template, backup)

html = template.read_text(encoding="utf-8")
css_tag = '<link rel="stylesheet" href="/static/biosafe_stage10/biosafe_workflow_ui.css">'
js_tag = '<script defer src="/static/biosafe_stage10/biosafe_workflow_ui.js"></script>'

if css_tag not in html:
    if "</head>" not in html:
        shutil.copy2(backup, template)
        raise SystemExit("No </head> tag found; original restored.")
    html = html.replace("</head>", f"  {css_tag}\n</head>", 1)

if js_tag not in html:
    if "</body>" not in html:
        shutil.copy2(backup, template)
        raise SystemExit("No </body> tag found; original restored.")
    html = html.replace("</body>", f"  {js_tag}\n</body>", 1)

template.write_text(html, encoding="utf-8")

print("BioSafe Stage 10.2 Workflow UI v0.1: INSTALLED")
print("Inference/API behavior modified: NO")
print("Template:", template)
print("Static assets:", assets_dir)
print("Backup:", backup)
