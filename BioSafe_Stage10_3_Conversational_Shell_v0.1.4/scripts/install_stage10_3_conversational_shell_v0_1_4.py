from pathlib import Path
import shutil, datetime

ROOT=Path("/home/khengoon/biosafe/stage9_local_shell")
HERE=Path(__file__).resolve().parent.parent
template=next((p for p in [ROOT/"app"/"templates"/"index.html",ROOT/"templates"/"index.html"] if p.exists()),None)
if template is None: raise SystemExit("Stage 9 index.html not found.")

html=template.read_text(encoding="utf-8")
required=[
'id="ask"','id="review"','id="forme"','id="askQuery"','id="reviewFile"',
'id="reviewQuery"','id="formEQuery"','id="status"','id="output"',
'onclick="runAsk()"','onclick="runReview()"','onclick="runFormE()"'
]
missing=[x for x in required if x not in html]
if missing: raise SystemExit("Stage 9 handler/DOM compatibility failed: "+", ".join(missing))

static=next((p for p in [ROOT/"app"/"static",ROOT/"static"] if p.exists()),ROOT/"app"/"static")
assets=static/"biosafe_stage10"; assets.mkdir(parents=True,exist_ok=True)
for n in ["biosafe_conversational_shell.css","biosafe_conversational_shell.js"]:
    shutil.copy2(HERE/"assets"/n,assets/n)

stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
backup=template.with_suffix(f".html.bak_stage10_3_v014_{stamp}")
shutil.copy2(template,backup)

lines=[l for l in html.splitlines() if "biosafe_conversational_shell.css" not in l and "biosafe_conversational_shell.js" not in l]
html="\n".join(lines)
css='<link rel="stylesheet" href="/static/biosafe_stage10/biosafe_conversational_shell.css">'
js='<script defer src="/static/biosafe_stage10/biosafe_conversational_shell.js"></script>'
if "</head>" not in html or "</body>" not in html: raise SystemExit("Template closing tags missing.")
html=html.replace("</head>",f"  {css}\n</head>",1).replace("</body>",f"  {js}\n</body>",1)
template.write_text(html+"\n",encoding="utf-8")

print("BioSafe Stage 10.3 Conversational Shell v0.1.4: INSTALLED")
print("Stage 9 inline handlers preserved: PASS")
print("DOM compatibility: PASS")
print("Inference/API behavior modified: NO")
print("Backup:",backup)
