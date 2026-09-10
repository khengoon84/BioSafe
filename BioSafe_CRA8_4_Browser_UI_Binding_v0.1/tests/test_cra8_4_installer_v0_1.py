from pathlib import Path
import tempfile, subprocess, os, sys, shutil

ROOT=Path(tempfile.mkdtemp(prefix="biosafe_cra84_"))
try:
    (ROOT/"app"/"static"/"biosafe_stage10").mkdir(parents=True)
    (ROOT/"app"/"main.py").write_text(
"""from flask import Flask, request, jsonify
app = Flask(__name__)
@app.get("/")
def index():
    return "ok"
@app.post("/api/ask")
def ask():
    return jsonify({"legacy": True})
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8765, debug=False)
""",encoding="utf-8")
    (ROOT/"app"/"static"/"app.js").write_text(
"""const output = document.getElementById('output');
const statusEl = document.getElementById('status');
async function showRequest(promise) {}
function runAsk() { fetch('/api/ask'); }
function runFormE() { fetch('/api/form-e'); }
function runReview() { fetch('/api/review'); }
""",encoding="utf-8")
    (ROOT/"app"/"static"/"biosafe_stage10"/"biosafe_conversational_shell.js").write_text(
"""function renderOutputMirror(raw){
  let obj=JSON.parse(raw);
  const conclusion=(obj.conclusion||"").trim();
  if(obj._meta){
    const dev=E("details","biosafe-developer-details");
    dev.append(E("summary","","Developer details"));
    const pre=E("pre",""); pre.textContent=JSON.stringify(obj._meta,null,2);
    dev.append(pre); b.append(dev);
  }
}
function resetChat(){
  const s=document.querySelector(".biosafe-chat-stream");
}
const x="biosafe-chat-app";
""",encoding="utf-8")

    script=Path(__file__).resolve().parent.parent/"scripts"/"install_cra8_4_v0_1.py"
    r=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,
                     env={**os.environ,"BIOSAFE_ROOT":str(ROOT)})
    print(r.stdout)
    if r.returncode:
        print(r.stderr); raise SystemExit(r.returncode)

    main=(ROOT/"app"/"main.py").read_text()
    appjs=(ROOT/"app"/"static"/"app.js").read_text()
    shell=(ROOT/"app"/"static"/"biosafe_stage10"/"biosafe_conversational_shell.js").read_text()

    checks={
      "proxy ask":'@app.post("/api/cra/ask")' in main,
      "proxy review":'@app.post("/api/cra/review")' in main,
      "proxy form-e":'@app.post("/api/cra/form-e")' in main,
      "proxy reset":'@app.post("/api/cra/session/reset")' in main,
      "proxy before app.run":main.index('@app.post("/api/cra/ask")') < main.index('if __name__ == "__main__":'),
      "legacy ask preserved":'@app.post("/api/ask")' in main,
      "browser CRA ask":"fetch('/api/cra/ask'" in appjs,
      "browser CRA review":"fetch('/api/cra/review'" in appjs,
      "browser CRA form-e":"fetch('/api/cra/form-e'" in appjs,
      "session localStorage":"biosafe_cra_session_id_v1" in appjs,
      "metadata stripped":"delete response._cra_quality" in appjs and "delete response._cra_adapter" in appjs and "delete response._meta" in appjs,
      "direct_answer supported":"obj.direct_answer||obj.conclusion" in shell,
      "developer details hidden":"Developer details" not in shell,
      "new conversation resets CRA":"BioSafeCRAClient?.resetSession" in shell,
      "backup created":len(list((ROOT/"app").glob("main.py.bak_cra8_4_v01_*")))==1,
    }
    for k,v in checks.items():
        print(("PASS" if v else "FAIL"),k)
    print(f"\nSummary: {sum(checks.values())}/{len(checks)} passed")
    if not all(checks.values()): raise SystemExit(1)
    print("CRA-8.4 installer integration test: PASS")
finally:
    shutil.rmtree(ROOT,ignore_errors=True)
