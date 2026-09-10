from dataclasses import dataclass
from typing import Optional
from cra_contracts_v0_1 import ConversationState, CaseState, InteractionType
from interaction_manager_v0_1 import classify_interaction
from reference_resolver_v0_1 import resolve_reference
from clarification_resolver_v0_1 import apply_clarification_response

@dataclass
class TurnProcessingResult:
    interaction: object
    resolved_reference: Optional[str]
    resolved_clarification_field: Optional[str]
    conversation_state: ConversationState
    case_state: CaseState

def process_turn(text,turn_id,conversation_state,case_state):
    interaction=classify_interaction(text,conversation_state)
    resolved_reference=None
    resolved_field=None
    conversation_state.active_interaction=interaction.interaction_type

    if interaction.interaction_type==InteractionType.FOLLOW_UP:
        resolved_reference=resolve_reference(text,conversation_state)
        if resolved_reference:
            interaction.referential_target=resolved_reference
    elif interaction.interaction_type==InteractionType.CLARIFICATION_RESPONSE:
        conversation_state,case_state,resolved_field=apply_clarification_response(conversation_state,case_state,text,turn_id)
        if resolved_field:
            interaction.referential_target=resolved_field

    return TurnProcessingResult(interaction,resolved_reference,resolved_field,conversation_state,case_state)
