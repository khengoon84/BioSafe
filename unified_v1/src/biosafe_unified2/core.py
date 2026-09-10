from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List
import re, uuid
from biosafe_unified226 import parse_act
FOLLOWUP_PATTERNS=(r"^\s*(please\s+)?elaborate[.!?]*\s*$",r"^\s*(please\s+)?explain\s+(that|this|it)(\s+more|\s+simply)?[.!?]*\s*$",r"^\s*why[.!?]*\s*$",r"^\s*what\s+do\s+you\s+mean[.!?]*\s*$",r"^\s*does\s+that\s+apply(\s+to\s+.*)?[.!?]*\s*$")
PRODUCT_HELP_EXACT={"who are you","what can you do","do you know who i am","do u know who i am","do you know me","do u know me"}
FORM_E_HINTS=("form e","biosafety form e","application form e")
DOC_REVIEW_HINTS=("review this","review the","check this","assess this","biosafety gaps","regulatory gaps")
REG_HINTS=("regulation","regulatory","law","legal","notify","notification","approval","approve","director general","act 678","biosafety act","comply","compliance","requirement","required")
EDU_HINTS=("what is","what are","difference between","difference of","define","explain","meaning of","what does","what do")
def canon(q:str)->str:
    return re.sub(r"[\s.!?]+$","",q.strip().lower())
@dataclass
class Turn: role:str; text:str
@dataclass
class CaseState:
    facts:Dict[str,Any]=field(default_factory=dict); sources:Dict[str,str]=field(default_factory=dict)
    def set_fact(self,key,value,source="conversation"):
        if value not in (None,"",[],{}): self.facts[key]=value; self.sources[key]=source
@dataclass
class SessionState:
    session_id:str; turns:List[Turn]=field(default_factory=list); case:CaseState=field(default_factory=CaseState)
    active_subject:str|None=None; active_concept:str|None=None
    def add(self,role,text):
        if text: self.turns.append(Turn(role,text)); self.turns=self.turns[-20:]
    def previous_assistant_text(self):
        for t in reversed(self.turns):
            if t.role=="assistant" and t.text.strip(): return t.text.strip()
        return None
    def previous_user_text(self):
        for t in reversed(self.turns):
            if t.role=="user" and t.text.strip(): return t.text.strip()
        return None
    def remember_topic(self,subject=None,concept=None):
        if subject: self.active_subject=subject
        if concept: self.active_concept=concept
class IntentRouter:
    def is_genuine_followup(self,query): return any(re.match(p,query.strip(),flags=re.I) for p in FOLLOWUP_PATTERNS)
    def classify(self,query,attachments=None):
        q=canon(query); attachments=attachments or []
        if q in PRODUCT_HELP_EXACT: return "product_help"
        if not q and attachments: return "document_review"
        if any(h in q for h in FORM_E_HINTS): return "form_e_assist"
        if attachments and any(h in q for h in DOC_REVIEW_HINTS): return "document_review"
        if self.is_genuine_followup(query): return "follow_up"
        if any(h in q for h in REG_HINTS): return "regulatory_assessment"
        if any(h in q for h in EDU_HINTS): return "educational_answer"
        if parse_act(query).get("act") == "greeting": return "greeting"
        return "simple_answer"
class CaseStateExtractor:
    def extract(self,text,source="conversation"):
        t=text or ""; low=t.lower(); out={}
        if "malaysia" in low or "my country" in low: out["jurisdiction"]="Malaysia"
        if "contained use" in low or "contained facility" in low: out["contained_use"]=True
        if any(x in low for x in ("recombinant","genetically modified","gmo","lmo")): out["genetic_modification_mentioned"]=True
        m=re.search(r"\b(?:using|with|work(?:ing)? with)\s+([A-Z][A-Za-z.-]+(?:\s+[a-z][A-Za-z.-]+)?)",t)
        if m: out["organism_text"]=m.group(1)
        return out
class DynamicElicitationEngine:
    def missing_for(self,intent,case,query):
        q=query.lower(); f=case.facts; missing=[]
        if intent=="regulatory_assessment":
            malaysia_reg=any(x in q for x in ("act 678","biosafety act","director general","form e","biosafety regulations"))
            if malaysia_reg and f.get("jurisdiction")!="Malaysia": missing.append({"field":"jurisdiction","question":"Which country or jurisdiction should I assess?","why":"Regulatory applicability depends on jurisdiction."})
            if any(x in q for x in ("act 678","director general","form e","biosafety regulations")) and not f.get("genetic_modification_mentioned"):
                missing.append({"field":"modern_biotechnology_trigger","question":"Does the project involve genetic modification, an LMO, or another modern-biotechnology technique?","why":"This fact can determine whether the Malaysian Biosafety Act/Regulations pathway is relevant."})
        if intent=="form_e_assist":
            if not f.get("organism_text"): missing.append({"field":"organism","question":"What organism or biological system is involved?","why":"Form E assistance must be based on project facts rather than assumptions."})
            if not f.get("genetic_modification_mentioned"): missing.append({"field":"modification","question":"What genetic modification or modern-biotechnology activity is involved?","why":"BioSafe must not infer the regulatory trigger or construct details."})
        return missing
class UnifiedOrchestrator:
    def __init__(self): self.router=IntentRouter(); self.extractor=CaseStateExtractor(); self.elicitor=DynamicElicitationEngine(); self.sessions={}
    def get_session(self,session_id=None):
        sid=session_id or f"unified-{uuid.uuid4().hex[:12]}"
        if sid not in self.sessions: self.sessions[sid]=SessionState(sid)
        return self.sessions[sid]
    def reset(self,session_id): return self.sessions.pop(session_id,None) is not None
    def prepare(self,query,session_id=None,attachments=None):
        s=self.get_session(session_id); attachments=attachments or []; intent=self.router.classify(query,attachments); previous=s.previous_assistant_text()
        # Capture the previous turn's subject/concept BEFORE the current query is
        # stored, so continuations ("elaborate more", "I just want to understand")
        # can bind to the prior turn.
        prev_user_text = s.previous_user_text()
        prev_turn = parse_act(prev_user_text or "") if prev_user_text else {}
        current_turn = parse_act(
            query,
            attachments=attachments,
            previous_subject=s.active_subject or prev_turn.get("subject"),
            previous_concept=s.active_concept or prev_turn.get("concept"),
        )
        s.remember_topic(current_turn.get("subject"), current_turn.get("concept"))
        for k,v in self.extractor.extract(query).items(): s.case.set_fact(k,v,"conversation")
        s.add("user",query); workflow={"document_review":"review","form_e_assist":"form-e"}.get(intent,"ask"); missing=self.elicitor.missing_for(intent,s.case,query)
        return {"session_id":s.session_id,"intent":intent,"workflow":workflow,"query":query,"original_query":query,"attachments":attachments,"case_state":dict(s.case.facts),"missing_information":missing,"resolved_reference":previous,"previous_subject":s.active_subject,"previous_concept":s.active_concept,"conversation_act":current_turn,"requires_retrieval":intent in {"educational_answer","regulatory_assessment","document_review","form_e_assist"},"constitution_version":"BioSafe Behavioral Constitution v1.0"}
    def remember_assistant(self,session_id,text):
        s=self.sessions.get(session_id)
        if s and text: s.add("assistant",text)
        return bool(s)
def strip_internal_metadata(payload):
    blocked={"_meta","_cra_adapter","_cra_quality","task_frame","activated_domains","inactive_domains","route","response_mode","internal_safety_classification","developer_details","_unified2"}
    if isinstance(payload,dict): return {k:strip_internal_metadata(v) for k,v in payload.items() if k not in blocked}
    if isinstance(payload,list): return [strip_internal_metadata(v) for v in payload]
    return payload
def dedupe_user_sections(payload):
    p=dict(payload)
    if "what_i_need_from_you" not in p and "information_needed" in p: p["what_i_need_from_you"]=p.pop("information_needed")
    else: p.pop("information_needed",None)
    if "next_step" not in p and "recommended_next_steps" in p: p["next_step"]=p.pop("recommended_next_steps")
    else: p.pop("recommended_next_steps",None)
    if "evidence" in p and "why_this_matters" in p and p["why_this_matters"]==p["evidence"]: p.pop("why_this_matters",None)
    return p
