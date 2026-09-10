import sys
from pathlib import Path
PKG=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(PKG/'src'))
from decision_quality_refinement_v0_1 import BioSafeDecisionQualityRefinementV01

g=BioSafeDecisionQualityRefinementV01()

def app_meta():
    return {'regulatory_applicability_guard':{'changed':True,'rule_ids':['RAGUARD-MY-LMO-001']}}

r=g.apply({
    '_meta': app_meta(),
    'conclusion':'Bacillus anthracis is a Class 1.5 risk organism requiring containment and PPE, not transport or disposal per MOH guidelines. Immediate isolation and biocontainment are required.',
    'applicable_authority':['Department of Biosafety / Malaysia','Ministry of Health Malaysia'],
    'evidence':[
        {'evidence_id':'CLM-013','statement':'A defensible risk assessment should contain enough background and detail for reviewers to understand hazards.'},
        {'evidence_id':'CLM-014','statement':'Risk assessment should be reviewed and updated.'},
        {'evidence_id':'CLM-028','statement':'The MOH clinical-specimen transport guideline does not serve as the clinical-waste guideline.'}
    ],
    'missing_information':['Specific containment strategy (e.g., biosafety cabinet vs. standard lab)'],
    'recommended_next_step':['Isolate the sample in a Class 1.5 containment unit','Review current facility controls for Class 1.5 risk management'],
    'limitations':[],
    'safety':{'classification':'caution','response_mode':'answer','reason':''}
}, user_query='I am working with Bacillus antracts in my laboratory. Do I need to notify the Director General under the Biosafety Regulations?')

combined=' '.join([r.response.get('conclusion',''),*(r.response.get('recommended_next_step') or [])]).lower()
mi=' | '.join(r.response.get('missing_information',[])).lower()
checks=[
 ('DQ13-001-no-class-1.5','class 1.5' not in combined),
 ('DQ13-002-no-silent-anthracis','bacillus anthracis is' not in combined),
 ('DQ13-003-ask-before-concluding',r.response['safety']['response_mode']=='ask_before_concluding'),
 ('DQ13-004-confirm-organism','confirm the organism name' in mi),
 ('DQ13-005-no-ungrounded-containment-missing','specific containment strategy' not in mi),
]

r2=g.apply({
 'conclusion':'Bacillus anthracis is listed in Risk Group 3.',
 'evidence':[{'evidence_id':'X','statement':'Bacillus anthracis is listed in Risk Group 3.'}],
 'missing_information':[], 'recommended_next_step':[], 'limitations':[],
 'safety':{'classification':'normal','response_mode':'answer','reason':''}
}, user_query='What risk group is Bacillus anthracis listed under?')
checks.append(('DQ13-006-supported-classification-kept','risk group 3' in r2.response['conclusion'].lower()))

r3=g.apply({
 'conclusion':'Bacillus anthracis is a Class 1.5 organism.',
 'evidence':[{'evidence_id':'X','statement':'Risk assessment should consider uncertainty.'}],
 'missing_information':[], 'recommended_next_step':[], 'limitations':[],
 'safety':{'classification':'normal','response_mode':'answer','reason':''}
}, user_query='What classification applies to Bacillus anthracis?')
checks.append(('DQ13-007-unsupported-classification-blocked','class 1.5' not in r3.response['conclusion'].lower()))

failed=[name for name,ok in checks if not ok]
for name,ok in checks:
    print(('PASS' if ok else 'FAIL'), name)
print(f'\nSummary: {len(checks)-len(failed)}/{len(checks)} passed')
if failed:
    raise SystemExit('Failures: '+', '.join(failed))
print('Decision Quality Refinement v0.1.3 regression: PASS')
