from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from conversational_quality_v0_1 import *
assert detect_foundational_intent('what is biosafety? What is the difference with biosecurity?')=='biosafety_vs_biosecurity'
assert detect_foundational_intent('How do I know I need to comply with biosafety or biosecurity or both?')=='biosafety_biosecurity_applicability'
q,e=normalize_likely_entity('is bacillus antracts dangerous?'); assert e=='Bacillus anthracis' and 'anthracis' in q
assert detect_entity_card(q)=='bacillus_anthracis_general'
assert is_elaboration_request('i do not understand. Please elaborate')
r=sanitize_user_response({'conclusion':'I can continue from the previous context, but this turn does not require a new regulatory retrieval.'})
assert 'regulatory retrieval' not in r['direct_answer'].lower()
print('CRA-8.4.1 quality unit contract: 6/6 PASS')
