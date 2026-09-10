from pathlib import Path
import shutil,datetime
R=Path("/home/khengoon/biosafe/stage9_local_shell");H=Path(__file__).resolve().parent.parent
p=next((x for x in [R/"app"/"templates"/"index.html",R/"templates"/"index.html"] if x.exists()),None)
if not p:raise SystemExit("Stage 9 index.html not found.")
h=p.read_text();req=['id="ask"','id="review"','id="forme"','id="askQuery"','id="reviewFile"','id="reviewQuery"','id="formEQuery"','id="status"','id="output"'];bad=[x for x in req if x not in h]
if bad:raise SystemExit("DOM compatibility failed: "+", ".join(bad))
s=next((x for x in [R/"app"/"static",R/"static"] if x.exists()),R/"app"/"static");a=s/"biosafe_stage10";a.mkdir(parents=True,exist_ok=True)
for n in ["biosafe_conversational_shell.css","biosafe_conversational_shell.js"]:shutil.copy2(H/"assets"/n,a/n)
b=p.with_suffix(".html.bak_stage10_3_"+datetime.datetime.now().strftime("%Y%m%d_%H%M%S"));shutil.copy2(p,b)
h="\n".join(l for l in h.splitlines() if "biosafe_conversational_shell." not in l)
h=h.replace("</head>",'  <link rel="stylesheet" href="/static/biosafe_stage10/biosafe_conversational_shell.css">\n</head>',1).replace("</body>",'  <script defer src="/static/biosafe_stage10/biosafe_conversational_shell.js"></script>\n</body>',1);p.write_text(h+"\n")
print("BioSafe Stage 10.3 Conversational Shell v0.1: INSTALLED");print("DOM compatibility: PASS");print("Inference/API behavior modified: NO");print("Backup:",b)
