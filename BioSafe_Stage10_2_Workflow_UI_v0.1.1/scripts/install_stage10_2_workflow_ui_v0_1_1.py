from pathlib import Path
import shutil, datetime

ROOT=Path("/home/khengoon/biosafe/stage9_local_shell")
HERE=Path(__file__).resolve().parent.parent

templates=[ROOT/"app"/"templates"/"index.html", ROOT/"templates"/"index.html"]
template=next((p for p in templates if p.exists()),None)
if template is None:
    raise SystemExit("Could not locate Stage 9 index.html. No files changed.")

html=template.read_text(encoding="utf-8")
required=['id="ask"','id="review"','id="forme"','id="askQuery"','id="reviewFile"',
          'id="reviewQuery"','id="formEQuery"','id="status"','id="output"']
missing=[x for x in required if x not in html]
if missing:
    raise SystemExit("Stage 9 DOM compatibility check failed. Missing: "+", ".join(missing))

static_candidates=[ROOT/"app"/"static",ROOT/"static"]
static_dir=next((p for p in static_candidates if p.exists()),None)
if static_dir is None:
    static_dir=ROOT/"app"/"static" if (ROOT/"app").exists() else ROOT/"static"
    static_dir.mkdir(parents=True,exist_ok=True)

assets_dir=static_dir/"biosafe_stage10"
assets_dir.mkdir(parents=True,exist_ok=True)
for name in ["biosafe_workflow_ui.css","biosafe_workflow_ui.js"]:
    shutil.copy2(HERE/"assets"/name,assets_dir/name)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=template.with_suffix(f".html.bak_stage10_2_v011_{stamp}")
shutil.copy2(template,backup)

lines=[line for line in html.splitlines()
       if "biosafe_workflow_ui.css" not in line and "biosafe_workflow_ui.js" not in line]
html="\n".join(lines)

css_tag='<link rel="stylesheet" href="/static/biosafe_stage10/biosafe_workflow_ui.css">'
js_tag='<script defer src="/static/biosafe_stage10/biosafe_workflow_ui.js"></script>'

if "</head>" not in html or "</body>" not in html:
    shutil.copy2(backup,template)
    raise SystemExit("Expected </head> and </body> not found; original restored.")

html=html.replace("</head>",f"  {css_tag}\n</head>",1)
html=html.replace("</body>",f"  {js_tag}\n</body>",1)
template.write_text(html+"\n",encoding="utf-8")

print("BioSafe Stage 10.2 Workflow UI v0.1.1: INSTALLED")
print("DOM compatibility: PASS")
print("Inference/API behavior modified: NO")
print("Template:",template)
print("Backup:",backup)
