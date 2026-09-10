from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import Normalizer
from sklearn.metrics.pairwise import cosine_similarity

from retriever_base import BioSafeCFG01, QueryProfile

class BioSafeCFG02(BioSafeCFG01):
    """CFG-02: CFG-01 gates/metadata + hybrid lexical and offline dense LSA embeddings.

    Dense layer is deliberately local and deterministic: word/character TF-IDF is projected
    with TruncatedSVD and L2-normalized. This is an embedding baseline, not a neural sentence model.
    """
    def __init__(self, kb_path: str|Path, manifest_path: str|Path, dense_dim: int = 24):
        super().__init__(kb_path, manifest_path)
        corpus = [r['search_text'] for r in self.records]
        self.dense_word = TfidfVectorizer(ngram_range=(1,2), lowercase=True, sublinear_tf=True,
                                          min_df=1, max_features=5000)
        self.dense_char = TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), lowercase=True,
                                          sublinear_tf=True, min_df=1, max_features=8000)
        w = self.dense_word.fit_transform(corpus)
        c = self.dense_char.fit_transform(corpus)
        X = hstack([w, c], format='csr')
        max_dim = max(2, min(dense_dim, X.shape[0]-1, X.shape[1]-1))
        self.svd = TruncatedSVD(n_components=max_dim, random_state=42)
        dense = self.svd.fit_transform(X)
        self.normalizer = Normalizer(copy=False)
        self.dense_matrix = self.normalizer.fit_transform(dense)
        self.dense_dim = max_dim

    def _expand_query(self, query: str, p: QueryProfile) -> str:
        expanded_query = query
        if p.domain=='MY-FORME' and p.intent=='Form E':
            expanded_query += ' LMO description donor parent organism vector method trait modified trait gene identity function target information'
        elif p.domain=='MY-FORME' and p.intent=='scope_gate':
            expanded_query += ' IBC Assessment Report registered IBC researcher PI field scope boundary'
        elif p.domain=='MY-REG' and p.intent=='notification':
            expanded_query += ' contained use notification prior notification Director General'
        elif p.domain=='MY-RA' and p.intent=='risk_assessment':
            expanded_query += ' GMM hazards exposure release controls BSL human animal plant environment'
        return expanded_query

    def retrieve(self, query:str, top_k:int=5) -> Tuple[QueryProfile,List[Dict[str,Any]]]:
        p=self.classify(query)
        expanded_query=self._expand_query(query,p)
        # CFG-01 lexical score, kept exactly comparable.
        qv=self.vectorizer.transform([expanded_query])
        lexical=cosine_similarity(qv,self.matrix).ravel()

        # Dense LSA embedding score.
        qw=self.dense_word.transform([expanded_query])
        qc=self.dense_char.transform([expanded_query])
        qx=hstack([qw,qc],format='csr')
        qdense=self.svd.transform(qx)
        qdense=self.normalizer.transform(qdense)
        dense=cosine_similarity(qdense,self.dense_matrix).ravel()
        # LSA cosine can be slightly negative; map to [0,1] for stable fusion.
        dense01=np.clip((dense+1.0)/2.0,0.0,1.0)

        scored=[]
        for i,r in enumerate(self.records):
            if not self._eligible(r,p): continue
            lex=float(lexical[i]); emb=float(dense01[i])
            auth=self._authority_score(r,p); jur=self._jurisdiction_score(r,p)
            scope=self._scope_score(r,p); curr=self._currentness_score(r)
            # Predeclared 50:50 retrieval fusion within the same 60% relevance budget.
            # Metadata budget remains identical to CFG-01 for a fair comparison.
            hybrid=0.50*lex + 0.50*emb
            final=0.60*hybrid + 0.20*auth + 0.10*jur + 0.05*scope + 0.05*curr
            out=dict(r)
            out.update({'lexical_score':round(lex,6),'embedding_score':round(emb,6),
                        'hybrid_relevance_score':round(hybrid,6),'authority_score':round(auth,3),
                        'jurisdiction_score':round(jur,3),'scope_score':round(scope,3),
                        'currentness_score':round(curr,3),'final_score':round(final,6)})
            scored.append(out)
        scored.sort(key=lambda x:(x['final_score'],x['hybrid_relevance_score'],x['retrieval_priority']),reverse=True)
        return p,scored[:top_k]
