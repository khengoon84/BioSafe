from typing import Optional, Any, Tuple
from cra_contracts_v0_1 import ConversationState, CaseState, FactValue, FactStatus, PendingClarification, AssistantConcept

class StateUpdateError(ValueError):
    pass

def add_pending_clarification(state, field, question, turn_id):
    state.pending_clarifications=[x for x in state.pending_clarifications if x.field!=field]
    state.pending_clarifications.append(PendingClarification(field=field,question=question,turn_id=turn_id))
    return state

def resolve_pending_clarification(state, field):
    state.pending_clarifications=[x for x in state.pending_clarifications if x.field!=field]
    return state

def add_assistant_concept(state, concept_id, label, turn_id, max_items=8):
    state.recent_assistant_concepts.append(AssistantConcept(concept_id=concept_id,label=label,turn_id=turn_id))
    state.recent_assistant_concepts=state.recent_assistant_concepts[-max_items:]
    return state

def update_case_fact(case, name, value, status, source=None, confidence=None, allow_replace_confirmed=False):
    if status==FactStatus.UNKNOWN and value is not None:
        raise StateUpdateError("unknown fact cannot contain a value")
    previous=case.facts.get(name)
    if previous and previous.status==FactStatus.USER_CONFIRMED and previous.value!=value and not allow_replace_confirmed:
        case.facts[name]=FactValue(value=None,status=FactStatus.DISPUTED,source=f"conflict: {previous.value!r} vs {value!r}",confidence=None)
        if name not in case.open_questions:
            case.open_questions.append(name)
        return case
    case.facts[name]=FactValue(value=value,status=status,source=source,confidence=confidence)
    if status in {FactStatus.USER_CONFIRMED,FactStatus.DOCUMENT_EXTRACTED,FactStatus.AUTHORITY_DERIVED}:
        case.open_questions=[x for x in case.open_questions if x!=name]
    elif status in {FactStatus.UNKNOWN,FactStatus.DISPUTED} and name not in case.open_questions:
        case.open_questions.append(name)
    return case

def promote_user_confirmation(state,case,field,value,source_turn):
    case=update_case_fact(case,field,value,FactStatus.USER_CONFIRMED,source=f"user:{source_turn}",confidence=1.0)
    state=resolve_pending_clarification(state,field)
    return state,case

def set_domains(case,activate=None,deactivate=None):
    active=set(case.active_domains); inactive=set(case.inactive_domains)
    for d in (activate or []):
        active.add(d); inactive.discard(d)
    for d in (deactivate or []):
        inactive.add(d); active.discard(d)
    case.active_domains=sorted(active); case.inactive_domains=sorted(inactive)
    return case
