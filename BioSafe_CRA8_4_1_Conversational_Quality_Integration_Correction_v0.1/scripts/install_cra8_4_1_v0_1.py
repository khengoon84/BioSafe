from pathlib import Path
import shutil,datetime
ROOT=Path('/home/khengoon/biosafe'); HERE=Path(__file__).resolve().parent.parent; dst=ROOT/'cra_v1'/'src'; scripts=ROOT/'cra_v1'/'scripts'; tests=ROOT/'cra_v1'/'tests'
stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
dst.mkdir(parents=True,exist_ok=True); scripts.mkdir(parents=True,exist_ok=True); tests.mkdir(parents=True,exist_ok=True)
for name in ['interaction_manager_v0_1.py','conversational_quality_v0_1.py','cra_service_runtime_v0_1_2.py','cra_bridge_app_v0_1_2.py']:
    target=dst/name
    if target.exists(): shutil.copy2(target,target.with_name(target.name+f'.bak_cra8_4_1_v01_{stamp}'))
    shutil.copy2(HERE/'src'/name,target)
for name in ['run_cra8_4_1_sidecar_v0_1.py']:
    shutil.copy2(HERE/'scripts'/name,scripts/name)
for name in ['live_regression_cra8_4_1_v0_1.py']:
    shutil.copy2(HERE/'tests'/name,tests/name)
print('BioSafe CRA-8.4.1 Conversational Quality Integration Correction v0.1: INSTALLED')
print('Frozen inference/RAG modified: NO')
print('Port remains: 8767')
print('Restart corrected sidecar to activate CRA-8.4.1.')
