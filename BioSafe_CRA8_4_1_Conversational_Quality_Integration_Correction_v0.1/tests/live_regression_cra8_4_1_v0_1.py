import json,urllib.request
BASE='http://127.0.0.1:8767'
def post(path,p):
    req=urllib.request.Request(BASE+path,data=json.dumps(p).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=120) as r:return r.status,json.loads(r.read())
def answer(d):
    r=d.get('response') or {}; return (r.get('direct_answer') or r.get('conclusion') or '')
checks=[]
s,d=post('/api/ask',{'query':'who are you'}); sid=d['session_id']; checks.append(('identity',s==200 and 'BioSafe' in answer(d)))
s,d=post('/api/ask',{'query':'what is biosafety? What is the difference with biosecurity?','session_id':sid}); a=answer(d).lower(); checks.append(('definitions',s==200 and 'unintentional' in a and 'unauthorized' in a and not d['response'].get('missing_information')))
s,d=post('/api/ask',{'query':'How do I know I need to comply with biosafety or biosecurity or both?','session_id':sid}); a=answer(d).lower(); checks.append(('applicability',s==200 and 'risk assessment' in a and not d['response'].get('missing_information')))
s,d=post('/api/ask',{'query':'is bacillus antracts dangerous?','session_id':sid}); a=answer(d).lower(); checks.append(('entity_typo',s==200 and 'bacillus anthracis' in a and 'anthrax' in a and 'regulatory retrieval' not in a))
s,d=post('/api/ask',{'query':'i do not understand. Please elaborate','session_id':sid}); a=answer(d).lower(); checks.append(('elaboration',s==200 and 'regulatory retrieval' not in a and len(a)>80))
for n,ok in checks: print(n,'PASS' if ok else 'FAIL')
if not all(x[1] for x in checks): raise SystemExit('CRA-8.4.1 live regression: FAIL')
print('CRA-8.4.1 live regression: 5/5 PASS')
