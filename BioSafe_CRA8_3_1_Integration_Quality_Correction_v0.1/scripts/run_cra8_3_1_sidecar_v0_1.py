from cra_bridge_app_v0_1_1 import create_app
print("BioSafe CRA-8.3.1 corrected sidecar: http://127.0.0.1:8767")
print("Existing CRA-8.2 sidecar (8766) and browser/UI (8765) remain available for rollback.")
create_app().run(host="127.0.0.1",port=8767,debug=False)
