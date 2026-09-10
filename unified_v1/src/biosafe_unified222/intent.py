
from __future__ import annotations
import re

def canonicalize(text:str)->str:
    s=(text or "").lower().strip()
    s=re.sub(r"[’']", "", s)
    s=re.sub(r"[^a-z0-9\s]+"," ",s)
    s=re.sub(r"\s+"," ",s).strip()
    # conversational orthography only; not domain semantics
    tokens=s.split()
    repl={"u":"you","r":"are","ur":"your"}
    return " ".join(repl.get(t,t) for t in tokens)

def normalize_intent(query:str, upstream_intent:str)->str:
    c=canonicalize(query)
    product_identity={
        "who are you","what are you","what can you do",
        "tell me about yourself"
    }
    self_knowledge={
        "do you know who i am","do you know me",
        "who am i","what do you know about me"
    }
    if c in product_identity: return "product_help"
    if c in self_knowledge: return "self_knowledge"
    return upstream_intent or "simple_answer"
