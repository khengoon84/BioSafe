from pathlib import Path
import shutil, datetime, re

ROOT=Path("/home/khengoon/biosafe/stage9_local_shell")
HERE=Path(__file__).resolve().parent.parent
template=next((p for p in [ROOT/"app"/"templates"/"index.html",ROOT/"templates"/"index.html"] if p.exists()),None)
if template is None:
    raise SystemExit("Stage 9 index.html not found.")

html=template.read_text(encoding="utf-8")
required=[
    'id="askQuery"','id="reviewQuery"','id="formEQuery"','id="output"',
    'biosafe_conversational_shell.css','biosafe_conversational_shell.js'
]
missing=[x for x in required if x not in html]
if missing:
    raise SystemExit("Stage 10.3 v0.1.4 prerequisite/DOM compatibility failed: "+", ".join(missing))

static=next((p for p in [ROOT/"app"/"static",ROOT/"static"] if p.exists()),ROOT/"app"/"static")
assets=static/"biosafe_stage10"
assets.mkdir(parents=True,exist_ok=True)
for name in ["biosafe_conversational_intelligence.css","biosafe_conversational_intelligence.js"]:
    shutil.copy2(HERE/"assets"/name,assets/name)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=template.with_suffix(f".html.bak_stage10_3_1_v01_{stamp}")
shutil.copy2(template,backup)

# Remove older Stage 10.3.1 tags if rerunning.
lines=[l for l in html.splitlines()
       if "biosafe_conversational_intelligence.css" not in l
       and "biosafe_conversational_intelligence.js" not in l]
html="\n".join(lines)

css='<link rel="stylesheet" href="/static/biosafe_stage10/biosafe_conversational_intelligence.css">'
js='<script defer src="/static/biosafe_stage10/biosafe_conversational_intelligence.js"></script>'
html=html.replace("</head>",f"  {css}\n</head>",1)
html=html.replace("</body>",f"  {js}\n</body>",1)
template.write_text(html+"\n",encoding="utf-8")

print("BioSafe Stage 10.3.1 Conversational Intelligence v0.1: INSTALLED")
print("Conversational Intent Gate: ENABLED")
print("Conversation Context Manager: ENABLED")
print("Educational Response Layer: ENABLED")
print("DQ-LMO-001 product safeguard: ENABLED")
print("Frozen Stage 8/9 inference files modified: NO")
print("Backup:",backup)
