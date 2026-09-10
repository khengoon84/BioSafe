from __future__ import annotations
import re
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Set

DOMAIN_TERMS={
    "form_e":[r"\bform e\b",r"\bnbb/n/cu/10/form e\b"],
    "lmo_modern_biotechnology":[r"\blmo\b",r"\bliving modified organism\b",r"\bgenetic manipulation\b",r"\bvector/method\b",r"\bmodified trait\b"],
    "transport":[r"\btransport\b",r"\btriple packaging\b",r"\bp620\b",r"\bp650\b",r"\bcategory a\b",r"\bcategory b\b"],
    "waste":[r"\bwaste\b",r"\bdisposal\b",r"\bscheduled waste\b"],
    "containment":[r"\bcontainment\b",r"\bbsl[- ]?\d\b",r"\bbiosafety level\b"],
}

SOURCE_DOMAIN_HINTS={
    "KB-MY-FORME":{"form_e"},
    "KB-MY-CU":{"lmo_modern_biotechnology"},
    "KB-MY-GMMRA":{"lmo_modern_biotechnology","containment"},
    "KB-MY-MOH2023":{"transport","clinical_specimen"},
    "KB-MY-DOE2005":{"waste"},
}

UNSUPPORTED_INSTITUTIONAL_PATTERNS=[
    r"\bsubmit\b.*\blaboratory director\b",
    r"\bsubmit\b.*\bibc\b",
    r"\bobtain\b.*\bclearance\b",
    r"\bseek\b.*\bapproval\b",
    r"\bobtain\b.*\bapproval\b",
    r"\bget\b.*\bapproval\b",
]

def _text(x: Any) -> str:
    if isinstance(x,str): return x
    if isinstance(x,dict):
        return " ".join(str(v) for v in x.values() if isinstance(v,(str,int,float)))
    return str(x)

def _source_id(item: Any) -> str:
    if isinstance(item,str): return item
    if isinstance(item,dict):
        for k in ("source_id","document_id","authority_id","id","source"):
            v=item.get(k)
            if isinstance(v,str): return v
    return ""

def _supported_domains_from_evidence(response: Dict[str,Any]) -> Set[str]:
    domains=set()
    for key in ("evidence","applicable_authority"):
        for item in response.get(key) or []:
            sid=_source_id(item)
            for hint,ds in SOURCE_DOMAIN_HINTS.items():
                if hint in sid:
                    domains |= set(ds)
            txt=_text(item).lower()
            for domain,patterns in DOMAIN_TERMS.items():
                if any(re.search(p,txt,re.I) for p in patterns):
                    domains.add(domain)
    return domains

def _mentioned_domains(text: str) -> Set[str]:
    out=set()
    for domain,patterns in DOMAIN_TERMS.items():
        if any(re.search(p,text,re.I) for p in patterns):
            out.add(domain)
    return out

def enforce_output_domain_and_recommendation_grounding(
    response: Dict[str,Any],
    *,
    active_domains: Iterable[str],
    excluded_domains: Iterable[str],
) -> tuple[Dict[str,Any], Dict[str,Any]]:
    out=deepcopy(response)
    active=set(active_domains or [])
    excluded=set(excluded_domains or [])
    evidence_domains=_supported_domains_from_evidence(out)
    removed=[]

    def sanitize_scalar(key):
        val=out.get(key)
        if not isinstance(val,str):
            return
        mentioned=_mentioned_domains(val)
        leaks=(mentioned & excluded) - active
        if leaks:
            out[key]="BioSafe can provide general information on this topic, but specific regulatory applicability requires additional project details."
            removed.append({"field":key,"domains":sorted(leaks),"reason":"excluded_domain_leakage"})

    def sanitize_list(key):
        vals=out.get(key)
        if not isinstance(vals,list):
            return
        kept=[]
        for item in vals:
            txt=_text(item)
            mentioned=_mentioned_domains(txt)
            leaks=(mentioned & excluded)-active
            if leaks:
                removed.append({"field":key,"text":txt,"domains":sorted(leaks),"reason":"excluded_domain_leakage"})
                continue

            if key=="recommended_next_step":
                unsupported_inst=any(re.search(p,txt,re.I) for p in UNSUPPORTED_INSTITUTIONAL_PATTERNS)
                if unsupported_inst:
                    # Require some active-domain evidence support before institutional workflow advice.
                    if not (active & evidence_domains):
                        removed.append({"field":key,"text":txt,"reason":"unsupported_institutional_recommendation"})
                        continue
                    # Even with domain evidence, approval/clearance verbs require explicit source text support.
                    evtxt=" ".join(_text(x) for x in (out.get("evidence") or []))
                    if not any(kw in evtxt.lower() for kw in ("approval","clearance","submit","ibc","director")):
                        removed.append({"field":key,"text":txt,"reason":"unsupported_institutional_recommendation"})
                        continue
            kept.append(item)
        out[key]=kept

    sanitize_scalar("conclusion")
    for k in ("missing_information","recommended_next_step","limitations"):
        sanitize_list(k)

    # Evidence and authority outside excluded domains are not retained.
    for key in ("evidence","applicable_authority"):
        vals=out.get(key)
        if not isinstance(vals,list):
            continue
        kept=[]
        for item in vals:
            txt=_text(item)
            sid=_source_id(item)
            item_domains=set()
            for hint,ds in SOURCE_DOMAIN_HINTS.items():
                if hint in sid: item_domains |= set(ds)
            item_domains |= _mentioned_domains(txt)
            leaks=(item_domains & excluded)-active
            if leaks:
                removed.append({"field":key,"text":txt,"domains":sorted(leaks),"reason":"excluded_domain_evidence"})
                continue
            kept.append(item)
        out[key]=kept

    meta={
        "removed_count":len(removed),
        "removed":removed,
        "active_domains":sorted(active),
        "excluded_domains":sorted(excluded),
        "evidence_domains":sorted(evidence_domains),
    }
    return out,meta
