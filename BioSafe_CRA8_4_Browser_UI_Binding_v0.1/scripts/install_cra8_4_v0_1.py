from __future__ import annotations
from pathlib import Path
import os, shutil, datetime, re

ROOT=Path(os.environ.get("BIOSAFE_ROOT","/home/khengoon/biosafe/stage9_local_shell"))
HERE=Path(__file__).resolve().parent.parent
stamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

main=next((p for p in [ROOT/"app"/"main.py",ROOT/"main.py"] if p.exists()),None)
appjs=next((p for p in [ROOT/"app"/"static"/"app.js",ROOT/"static"/"app.js"] if p.exists()),None)
shelljs=next((p for p in [
    ROOT/"app"/"static"/"biosafe_stage10"/"biosafe_conversational_shell.js",
    ROOT/"static"/"biosafe_stage10"/"biosafe_conversational_shell.js",
] if p.exists()),None)

if not main: raise SystemExit("BioSafe Stage 9 main.py not found under "+str(ROOT))
if not appjs: raise SystemExit("BioSafe Stage 9 app.js not found under "+str(ROOT))
if not shelljs: raise SystemExit("Stage 10.3 conversational shell JS not found under "+str(ROOT))

main_text=main.read_text(encoding="utf-8")
app_text=appjs.read_text(encoding="utf-8")
shell_text=shelljs.read_text(encoding="utf-8")

for required in ['app = Flask(','@app.get("/")','request','jsonify']:
    if required not in main_text: raise SystemExit("main.py compatibility check failed: "+required)
for required in ["function runAsk()","function runFormE()","function runReview()","showRequest"]:
    if required not in app_text: raise SystemExit("app.js compatibility check failed: "+required)
for required in ["function resetChat()","function renderOutputMirror(raw)","biosafe-chat-app"]:
    if required not in shell_text: raise SystemExit("conversational shell compatibility check failed: "+required)

for p in [main,appjs,shelljs]:
    shutil.copy2(p,p.with_name(p.name+f".bak_cra8_4_v01_{stamp}"))

begin="# === BIOSAFE CRA-8.4 PROXY BEGIN ==="
end="# === BIOSAFE CRA-8.4 PROXY END ==="
if begin in main_text and end in main_text:
    main_text=re.sub(re.escape(begin)+r".*?"+re.escape(end)+r"\n?","",main_text,flags=re.S).rstrip()+"\n"

proxy=(HERE/"patches"/"cra_proxy_block_v0_1.py.txt").read_text(encoding="utf-8").strip()
marker='if __name__ == "__main__":'
if marker in main_text:
    main_text=main_text.replace(marker,proxy+"\n\n"+marker,1)
else:
    main_text=main_text.rstrip()+"\n\n"+proxy+"\n"
main.write_text(main_text,encoding="utf-8")

appjs.write_text((HERE/"patches"/"app_cra_bound_v0_1.js").read_text(encoding="utf-8"),encoding="utf-8")

old='const conclusion=(obj.conclusion||"").trim();'
new='const conclusion=(obj.direct_answer||obj.conclusion||"").trim();'
if old in shell_text:
    shell_text=shell_text.replace(old,new,1)
elif new not in shell_text:
    raise SystemExit("Could not patch direct_answer rendering.")

# Remove ordinary-user developer details block.
shell_text=re.sub(
    r'\n\s*if\(obj\._meta\)\{\s*const dev=E\("details","biosafe-developer-details"\);.*?b\.append\(dev\);\s*\}',
    '',
    shell_text,
    count=1,
    flags=re.S
)

reset_old='function resetChat(){\n  const s=document.querySelector(".biosafe-chat-stream");'
reset_new='function resetChat(){\n  if(window.BioSafeCRAClient?.resetSession) window.BioSafeCRAClient.resetSession();\n  const s=document.querySelector(".biosafe-chat-stream");'
if reset_old in shell_text:
    shell_text=shell_text.replace(reset_old,reset_new,1)
elif reset_new not in shell_text:
    raise SystemExit("Could not patch CRA session reset.")

shelljs.write_text(shell_text,encoding="utf-8")

if str(ROOT).startswith("/home/khengoon/biosafe"):
    cra_tests=Path("/home/khengoon/biosafe/cra_v1/tests")
    cra_tests.mkdir(parents=True,exist_ok=True)
    shutil.copy2(HERE/"tests"/"live_smoke_cra8_4_proxy_v0_1.py",cra_tests/"live_smoke_cra8_4_proxy_v0_1.py")

print("BioSafe CRA-8.4 Browser/UI Binding v0.1: INSTALLED")
print("UI server: http://127.0.0.1:8765")
print("CRA target: http://127.0.0.1:8767")
print("Legacy API routes preserved: YES")
print("CRA routes added under /api/cra/*")
print("CRA session stored per browser via localStorage")
print("Internal CRA metadata visible to ordinary users: NO")
print("Backup suffix:",f".bak_cra8_4_v01_{stamp}")
