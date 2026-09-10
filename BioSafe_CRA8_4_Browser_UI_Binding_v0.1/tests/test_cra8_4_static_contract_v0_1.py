from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
app=(ROOT/"patches"/"app_cra_bound_v0_1.js").read_text()
proxy=(ROOT/"patches"/"cra_proxy_block_v0_1.py.txt").read_text()
checks={
 "same-origin ask":"/api/cra/ask" in app,
 "same-origin review":"/api/cra/review" in app,
 "same-origin form-e":"/api/cra/form-e" in app,
 "session id":"BIOSAFE_CRA_SESSION_KEY" in app,
 "metadata hidden":"delete response._meta" in app and "delete response._cra_quality" in app,
 "proxy target 8767":'http://127.0.0.1:8767' in proxy,
 "reset route":'/api/cra/session/reset' in proxy,
}
for k,v in checks.items():
    print(("PASS" if v else "FAIL"),k)
print(f"\nSummary: {sum(checks.values())}/{len(checks)} passed")
if not all(checks.values()): raise SystemExit(1)
print("CRA-8.4 static browser contract: PASS")
