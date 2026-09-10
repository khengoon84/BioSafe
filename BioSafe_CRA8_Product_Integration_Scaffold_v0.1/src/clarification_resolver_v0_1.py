import re
from state_manager_v0_1 import promote_user_confirmation

YES=re.compile(r"^\s*(yes|correct|confirmed|that'?s right)\s*[.!]?\s*$",re.I)
NO=re.compile(r"^\s*(no|incorrect|not that|that'?s wrong)\s*[.!]?\s*$",re.I)

def resolve_clarification_value(field,text):
    t=(text or "").strip()
    if not t:
        return None,False
    if field in {"lmo_status","genetically_modified","recombinant_status"}:
        if YES.match(t): return True,True
        if NO.match(t): return False,True
        if re.search(r"\b(not genetically modified|not recombinant|naturally occurring)\b",t,re.I): return False,True
        if re.search(r"\b(genetically modified|recombinant|modern biotechnology)\b",t,re.I): return True,True
    if field in {"organism_identity","material_identity","host_organism"}:
        if len(t.split())<=8 and len(t)<=120 and not YES.match(t) and not NO.match(t):
            return t,True
    if YES.match(t) or NO.match(t):
        return (True if YES.match(t) else False),True
    if len(t.split())<=12 and len(t)<=160:
        return t,True
    return None,False

def apply_clarification_response(state,case,text,turn_id):
    if not state.pending_clarifications:
        return state,case,None
    pending=state.pending_clarifications[0]
    value,resolved=resolve_clarification_value(pending.field,text)
    if not resolved:
        return state,case,None
    state,case=promote_user_confirmation(state,case,pending.field,value,turn_id)
    return state,case,pending.field
