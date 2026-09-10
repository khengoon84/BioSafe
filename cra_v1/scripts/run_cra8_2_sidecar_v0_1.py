from cra_bridge_app_v0_1 import create_app
print("BioSafe CRA-8.2 sidecar: http://127.0.0.1:8766")
print("Existing BioSafe UI/service on port 8765 remains unchanged.")
create_app().run(host="127.0.0.1",port=8766,debug=False)
