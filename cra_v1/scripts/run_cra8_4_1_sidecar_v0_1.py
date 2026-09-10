from cra_bridge_app_v0_1_2 import create_app
print('BioSafe CRA-8.4.1 corrected sidecar: http://127.0.0.1:8767')
create_app().run(host='127.0.0.1',port=8767,debug=False)
