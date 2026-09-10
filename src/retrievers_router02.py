from __future__ import annotations
import sys
from pathlib import Path
from typing import Tuple, List, Dict, Any
import numpy as np
from scipy.sparse import hstack
from sklearn.metrics.pairwise import cosine_similarity

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from retriever_base import BioSafeCFG01, QueryProfile
from retriever_cfg02_base import BioSafeCFG02
from router_v02 import BioSafeRouterV02, Route

class Router02Mixin:
    def _init_router02(self):
        self.router_v02=BioSafeRouterV02()

    def classify(self, query:str) -> QueryProfile:
        r=self.router_v02.classify(query)
        p=QueryProfile(r.jurisdiction,r.domain,r.intent,r.preferred_tier,r.scope,r.uncertainty_sensitive,r.safety_sensitive)
        # Attach diagnostic-only attributes without changing QueryProfile schema.
        p.expansion_terms=r.expansion_terms
        p.route_rationale=r.rationale
        return p

    def _router02_expand(self, query:str, p:QueryProfile) -> str:
        extra=getattr(p,'expansion_terms','')
        q=query.lower()
        # Router-level intent expansion only; retrieval scoring/weights remain frozen.
        if p.domain=='MY-FORME':
            if p.intent=='fee_exclusion':
                extra='fees excluded fee omission do not score fee BioSafe requirement'
            elif p.intent in {'annex_exclusion','scope_gate'} and ('annex' in q or 'assessment report' in q):
                extra='Annex 2 IBC Assessment Report researcher PI missing field excluded do not score'
            elif p.intent=='approval_boundary':
                extra='no approval claim decision support not official approval compliance determination'
            elif 'unintentionally released' in q or 'unintentional release' in q or 'risks to people' in q:
                extra='Form E A4.1 human health risks hazards likelihood consequence unintentional release environment'
            elif 'facility' in q or 'bsl' in q or 'inspection' in q:
                extra='Form E premises facility name type BSL inspection certification contact BSO'
            elif 'transport precautions' in q or 'decontamination' in q or 'contingency' in q or 'disposal' in q:
                extra='Form E transport precautions decontamination disposal contingency measures'
            elif p.intent=='uncertainty':
                extra='unknowns missing scientific regulatory facts clarification never infer organism construct BSL risk group facility class'
            else:
                extra='Form E LMO description donor parent organism host species vector method modified trait gene identity function target information'
        elif p.domain=='MY-IBC' and p.intent=='approval_boundary':
            extra='IBC boundary do not simulate issue IBC approval no approval claim decision support not official compliance determination'
        elif p.domain=='MY-REG' and p.intent=='notification':
            extra='notification complete without errors amendment completion resubmission Director General prior notification contained use'
        return (query+' '+extra).strip()

class BioSafeCFG01Router02(Router02Mixin, BioSafeCFG01):
    def __init__(self,kb_path,manifest_path):
        BioSafeCFG01.__init__(self,kb_path,manifest_path)
        self._init_router02()

    def retrieve(self, query:str, top_k:int=5):
        p=self.classify(query)
        expanded=self._router02_expand(query,p)
        qv=self.vectorizer.transform([expanded])
        lexical=cosine_similarity(qv,self.matrix).ravel()
        scored=[]
        for i,r in enumerate(self.records):
            if not self._eligible(r,p): continue
            lex=float(lexical[i]); auth=self._authority_score(r,p); jur=self._jurisdiction_score(r,p)
            scope=self._scope_score(r,p); curr=self._currentness_score(r)
            final=0.60*lex+0.20*auth+0.10*jur+0.05*scope+0.05*curr
            out=dict(r); out.update({'lexical_score':round(lex,6),'authority_score':round(auth,3),
                'jurisdiction_score':round(jur,3),'scope_score':round(scope,3),'currentness_score':round(curr,3),
                'final_score':round(final,6)})
            scored.append(out)
        scored.sort(key=lambda x:(x['final_score'],x['lexical_score'],x['retrieval_priority']),reverse=True)
        return p,scored[:top_k]

class BioSafeCFG02Router02(Router02Mixin, BioSafeCFG02):
    def __init__(self,kb_path,manifest_path,dense_dim=24):
        BioSafeCFG02.__init__(self,kb_path,manifest_path,dense_dim=dense_dim)
        self._init_router02()

    def retrieve(self, query:str, top_k:int=5):
        p=self.classify(query)
        expanded=self._router02_expand(query,p)
        qv=self.vectorizer.transform([expanded])
        lexical=cosine_similarity(qv,self.matrix).ravel()
        qw=self.dense_word.transform([expanded]); qc=self.dense_char.transform([expanded]); qx=hstack([qw,qc],format='csr')
        qdense=self.svd.transform(qx); qdense=self.normalizer.transform(qdense)
        dense=cosine_similarity(qdense,self.dense_matrix).ravel(); dense01=np.clip((dense+1.0)/2.0,0.0,1.0)
        scored=[]
        for i,r in enumerate(self.records):
            if not self._eligible(r,p): continue
            lex=float(lexical[i]); emb=float(dense01[i]); auth=self._authority_score(r,p); jur=self._jurisdiction_score(r,p)
            scope=self._scope_score(r,p); curr=self._currentness_score(r); hybrid=0.50*lex+0.50*emb
            final=0.60*hybrid+0.20*auth+0.10*jur+0.05*scope+0.05*curr
            out=dict(r); out.update({'lexical_score':round(lex,6),'embedding_score':round(emb,6),
                'hybrid_relevance_score':round(hybrid,6),'authority_score':round(auth,3),'jurisdiction_score':round(jur,3),
                'scope_score':round(scope,3),'currentness_score':round(curr,3),'final_score':round(final,6)})
            scored.append(out)
        scored.sort(key=lambda x:(x['final_score'],x['hybrid_relevance_score'],x['retrieval_priority']),reverse=True)
        return p,scored[:top_k]
