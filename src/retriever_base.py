from __future__ import annotations
import json, math, re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TOKEN_RE = re.compile(r"[a-z0-9]+")

def norm(s: str) -> str:
    return " ".join(TOKEN_RE.findall((s or "").lower()))

@dataclass
class QueryProfile:
    jurisdiction: str
    domain: str
    intent: str
    preferred_tier: str
    scope: List[str]
    uncertainty_sensitive: bool = False
    safety_sensitive: bool = False

class BioSafeCFG01:
    """CFG-01: deterministic classification + scope filtering + lexical TF-IDF + authority-aware ranking."""
    def __init__(self, kb_path: str|Path, manifest_path: str|Path):
        self.kb = json.load(open(kb_path, encoding='utf-8'))
        self.manifest = json.load(open(manifest_path, encoding='utf-8'))
        self.doc_meta = {d['document_id']: d for d in self.kb['documents']}
        self.manifest_meta = {r['record_id']: r for r in self.manifest['records']}
        self.records = self._build_records()
        corpus = [r['search_text'] for r in self.records]
        self.vectorizer = TfidfVectorizer(ngram_range=(1,2), lowercase=True, sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(corpus)

    def _build_records(self) -> List[Dict[str,Any]]:
        rows=[]
        for c in self.kb['claims']:
            d=self.doc_meta[c['document_id']]
            m=self.manifest_meta.get(c['document_id'], {})
            tier_num = int(str(d.get('authority_tier','Tier 3')).split()[-1]) if 'Tier' in str(d.get('authority_tier')) else int(m.get('authority_tier',3))
            row={
                'record_id': c['claim_id'], 'record_type':'claim', 'claim_id':c['claim_id'],
                'document_id':c['document_id'], 'title':d['title'], 'authority':d['authority'],
                'jurisdiction':d['jurisdiction'], 'authority_tier':tier_num,
                'document_type':d['document_type'], 'status':d['status'], 'section':c.get('section',''),
                'page':c.get('page',''), 'claim_type':c.get('claim_type',''), 'text':c.get('text',''),
                'priority':c.get('priority',''), 'verification_status':c.get('verification_status',''),
                'retrieval_priority':float(m.get('retrieval_priority',60)), 'scope':m.get('scope',[]),
                'must_cite':bool(m.get('must_cite',True)), 'source_url':d.get('source_url','')
            }
            row['search_text']=' '.join(map(str,[row['text'],row['claim_type'],row['title'],row['section'],' '.join(row['scope'])]))
            rows.append(row)
        # Retrieval/control rules are searchable control records. They are not regulatory evidence claims.
        for r in self.kb.get('retrieval_rules',[]):
            rows.append({
                'record_id':r['rule_id'], 'record_type':'control_rule','claim_id':r['rule_id'],
                'document_id':'SYSTEM CONTROL POLICY','title':'BioSafe Retrieval Control Policy','authority':'BioSafe system policy',
                'jurisdiction':'System','authority_tier':0,'document_type':'System control','status':'Current',
                'section':r.get('rule',''),'page':'','claim_type':'control_rule','text':r.get('implementation',''),
                'priority':'critical','verification_status':'Project rule','retrieval_priority':100.0,
                'scope':[r.get('rule','')], 'must_cite':False,'source_url':'',
                'search_text':' '.join([r.get('rule',''),r.get('implementation','')])
            })
        return rows

    def classify(self, query: str) -> QueryProfile:
        q=norm(query)
        safety = any(x in q for x in ['more harmful','harmful biological','facilitate harmful','dangerous biological'])
        if safety:
            return QueryProfile('System','SAFETY','refusal','System',['safety','refusal'],False,True)
        if 'form e' in q or 'ibc assessment report' in q or ('host species' in q and 'construct' in q):
            intent='scope_gate' if 'ibc assessment report' in q else ('uncertainty' if 'invent' in q or 'missing' in q else 'Form E')
            return QueryProfile('Malaysia','MY-FORME',intent,'Tier 2',['Form E','LMO description','IBC boundary'], intent=='uncertainty')
        if 'sw 404' in q or 'waste' in q or 'disposal' in q:
            if 'clinical specimen transport guideline' in q:
                return QueryProfile('Malaysia','TRANSPORT','transport_scope','Tier 2',['specimen classification','packaging','transport'])
            return QueryProfile('Malaysia','WASTE','waste','Tier 1+2',['scheduled waste','SW 404','storage','treatment','disposal'])
        if any(x in q for x in ['clinical specimen','infectious substance','transported','packaging','category a','category b']):
            return QueryProfile('Malaysia','TRANSPORT','transport','Tier 2',['specimen classification','Category A/B','packaging','labelling','transport'])
        if 'biosecurity' in q:
            return QueryProfile('International','WHO-BIOSEC','biosecurity','Tier 3',['biosecurity','access','inventory','secure handling','governance'])
        if 'who outrank' in q or ('malaysian regulatory' in q and 'who' in q):
            return QueryProfile('Malaysia','AUTHORITY','authority','Tier 1',['regulatory determination'])
        if 'older procedural' in q or 'current official operational' in q or 'conflicts with a current' in q:
            return QueryProfile('Malaysia','CURRENTNESS','versioning','Tier 2',['currentness'])
        if 'pi' in q and 'ibc' in q:
            return QueryProfile('Malaysia','MY-IBC','governance','Tier 2',['PI responsibilities','IBC governance'])
        if 'emergency response' in q or 'incident' in q:
            return QueryProfile('Malaysia','MY-INCIDENT','incident','Tier 1+2',['emergency response','incident response'])
        if 'gmm risk assessment' in q or ('scientific information' in q and 'missing' in q):
            return QueryProfile('Malaysia','MY-RA','uncertainty' if 'missing' in q else 'risk_assessment','Tier 1+2' if 'missing' in q else 'Tier 2',['risk assessment','uncertainty','GMM'], 'missing' in q)
        if 'laboratory risk' in q or 'assessing laboratory risk' in q:
            return QueryProfile('International','WHO-RA','risk_assessment','Tier 3',['risk assessment','uncertainty','agents','procedures','facility','competency'])
        if 'contained use' in q or 'contained-use' in q or 'lmo' in q or 'biosafety level' in q:
            intent='notification' if 'notification' in q else ('uncertainty' if 'low risk' in q else 'IBC/containment')
            return QueryProfile('Malaysia','MY-REG',intent,'Tier 1+2' if intent!='notification' else 'Tier 1',['notification','contained use','GM-BSL','containment'], intent=='uncertainty')
        return QueryProfile('Malaysia','GENERAL','general','Tier 1+2',[])

    def _eligible(self, r:Dict[str,Any], p:QueryProfile) -> bool:
        if p.safety_sensitive:
            return r['record_type']=='control_rule'
        # system control rules remain available for authority/scope/currentness/uncertainty cases
        if r['record_type']=='control_rule':
            return p.domain in {'AUTHORITY','CURRENTNESS','MY-FORME','MY-RA'} or p.uncertainty_sensitive
        if p.jurisdiction=='Malaysia' and r['jurisdiction'] not in {'Malaysia','International'}:
            return False
        if p.jurisdiction=='International' and r['jurisdiction']!='International':
            return False
        # hard domain gates
        did=r['document_id']
        if p.domain=='TRANSPORT': return did=='KB-MY-MOH2023'
        if p.domain=='WASTE': return did in {'KB-MY-DOE2005','KB-MY-CU','KB-WHO-LBM4'}
        if p.domain=='MY-FORME': return did in {'KB-MY-FORME','KB-MY-GMMRA'}
        if p.domain=='MY-IBC': return did in {'KB-MY-IBC','KB-MY-REG2010'}
        if p.domain=='MY-INCIDENT': return did in {'KB-MY-ACT678','KB-MY-CU','KB-MY-IBC'}
        if p.domain=='MY-RA': return did in {'KB-MY-GMMRA','KB-MY-ACT678'}
        if p.domain=='WHO-RA': return did in {'KB-WHO-RA','KB-WHO-LBM4'}
        if p.domain=='WHO-BIOSEC': return did=='KB-WHO-BIOSEC'
        if p.domain=='MY-REG': return did in {'KB-MY-ACT678','KB-MY-REG2010','KB-MY-CU','KB-MY-GMMRA','KB-MY-IBC'}
        if p.domain=='AUTHORITY': return did in {'KB-MY-ACT678','KB-MY-REG2010'}
        if p.domain=='CURRENTNESS': return did=='KB-MY-FORME'
        return True

    def _authority_score(self, r, p):
        if r['record_type']=='control_rule': return 1.0
        tier=r['authority_tier']
        # legal/regulatory Malaysia: Tier1 strongest; operational domains allow Tier2 close behind
        if p.jurisdiction=='Malaysia':
            if p.intent in {'notification','authority'}: tier_s={1:1.0,2:0.75,3:0.45}.get(tier,0.3)
            else: tier_s={1:1.0,2:0.95,3:0.65}.get(tier,0.3)
        else: tier_s={3:1.0,2:0.5,1:0.5}.get(tier,0.3)
        return tier_s

    def _jurisdiction_score(self,r,p):
        if r['record_type']=='control_rule': return 1.0
        if r['jurisdiction']==p.jurisdiction: return 1.0
        if p.jurisdiction=='Malaysia' and r['jurisdiction']=='International': return 0.45
        return 0.0

    def _scope_score(self,r,p):
        text=norm(' '.join(r.get('scope',[]))+' '+r.get('claim_type','')+' '+r.get('text',''))
        if not p.scope: return 0.5
        hits=sum(1 for s in p.scope if norm(s) in text)
        return min(1.0, hits/max(1,min(2,len(p.scope))))

    def _currentness_score(self,r):
        s=norm(r.get('status',''))
        return 1.0 if any(x in s for x in ['current','official','authoritative']) else 0.8

    def retrieve(self, query:str, top_k:int=5) -> Tuple[QueryProfile,List[Dict[str,Any]]]:
        p=self.classify(query)
        expanded_query = query
        if p.domain=='MY-FORME' and p.intent=='Form E':
            expanded_query += ' LMO description donor parent organism vector method trait modified trait gene identity function target information'
        elif p.domain=='MY-FORME' and p.intent=='scope_gate':
            expanded_query += ' IBC Assessment Report registered IBC researcher PI field scope boundary'
        elif p.domain=='MY-REG' and p.intent=='notification':
            expanded_query += ' contained use notification prior notification Director General'
        elif p.domain=='MY-RA' and p.intent=='risk_assessment':
            expanded_query += ' GMM hazards exposure release controls BSL human animal plant environment'
        qv=self.vectorizer.transform([expanded_query])
        lexical=cosine_similarity(qv,self.matrix).ravel()
        scored=[]
        for i,r in enumerate(self.records):
            if not self._eligible(r,p): continue
            lex=float(lexical[i])
            auth=self._authority_score(r,p); jur=self._jurisdiction_score(r,p); scope=self._scope_score(r,p); curr=self._currentness_score(r)
            # Authority-aware CFG-01. Lexical remains majority component.
            final=0.60*lex + 0.20*auth + 0.10*jur + 0.05*scope + 0.05*curr
            out=dict(r)
            out.update({'lexical_score':round(lex,6),'authority_score':round(auth,3),'jurisdiction_score':round(jur,3),'scope_score':round(scope,3),'currentness_score':round(curr,3),'final_score':round(final,6)})
            scored.append(out)
        scored.sort(key=lambda x:(x['final_score'],x['lexical_score'],x['retrieval_priority']), reverse=True)
        return p, scored[:top_k]
