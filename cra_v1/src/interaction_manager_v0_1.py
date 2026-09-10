import re
from typing import Optional, List
from cra_contracts_v0_1 import InteractionResult, InteractionType, ConversationState
PRODUCT_PATTERNS=[r"\bwhat can you do\b",r"\bhow can you help\b",r"\bwhat kind of document(?:s)? can you review\b",r"\bwhat document(?:s)? can you review\b",r"\bcan you review (?:an? )?(?:sop|proposal|document|form e|risk assessment)\b",r"\bhow does (?:the )?form e assistant work\b",r"\bhow do i use biosafe\b",r"\bwhat do you review\b"]
IDENTITY_PATTERNS=[r"^\s*who are you[?.! ]*$",r"^\s*what are you[?.! ]*$",r"^\s*tell me about yourself[?.! ]*$"]
SOCIAL_PATTERNS=[r"^\s*(hi|hello|hey|good morning|good afternoon|good evening|thanks|thank you)[!. ]*$"]
REFORMULATE_PATTERNS=[r"\bexplain (?:that|this) more simply\b",r"\bsimplify (?:that|this)\b",r"\bsummarize (?:that|this)\b",r"\bcan you explain (?:that|this)\b",r"^\s*(?:please\s+)?elaborate[?.! ]*$",r"^\s*(?:please\s+)?(?:explain|tell me) more[?.! ]*$",r"^\s*i (?:do not|don't) understand(?:[.!].*)?$" ]
FOLLOWUP_PATTERNS=[r"\bwhat (?:did you mean|do you mean) by\b",r"\bwhat (?:approval|requirement|regulation|rule|form|document) did you mean\b",r"^\s*why[?.! ]*$",r"\bdoes that apply to me\b",r"\bis that mandatory\b",r"\bis that compulsory\b",r"\bwhat about (?:the )?(?:first|second|third) (?:one|point)\b"]
TASK_CHANGE_PATTERNS=[r"\bactually\b.*\b(?:only|instead)\b",r"\bi only want to know about\b",r"\blet(?:'s| us) talk about\b",r"\bchange (?:the )?topic\b"]
SHORT_CONFIRM=re.compile(r"^\s*(yes|no|correct|incorrect|confirmed|not sure|unknown|none|n/?a)\s*[.!]?\s*$",re.I)
def _matches(text,patterns): return any(re.search(p,text,re.I) for p in patterns)
def _looks_like_explicit_question(t:str)->bool:
    # A short but self-contained domain question must not be consumed as an answer to an old clarification.
    if re.search(r"\b(biosafety|biosecurity|bacteri|virus|fung|pathogen|toxin|specimen|sample|lmo|gmm|form e|waste|transport)\w*\b",t,re.I): return True
    if re.match(r"^\s*(is|are|does|do|can|could|should|what|which|how|when|where|who)\b",t,re.I) and len(t.split())>=3: return True
    return False
def classify_interaction(text:str,state:Optional[ConversationState]=None)->InteractionResult:
    t=(text or "").strip()
    if not t:return InteractionResult(InteractionType.SOCIAL,0.99,candidate_task="empty_input",needs_domain_pipeline=False)
    if _matches(t,SOCIAL_PATTERNS):return InteractionResult(InteractionType.SOCIAL,0.99,candidate_task="social",needs_domain_pipeline=False)
    if _matches(t,IDENTITY_PATTERNS):return InteractionResult(InteractionType.PRODUCT_HELP,0.99,candidate_task="identity",needs_domain_pipeline=False)
    if _matches(t,PRODUCT_PATTERNS):return InteractionResult(InteractionType.PRODUCT_HELP,0.98,candidate_task="product_help",needs_domain_pipeline=False)
    if _matches(t,REFORMULATE_PATTERNS):return InteractionResult(InteractionType.REFORMULATE,0.97,referential_target="recent_assistant_answer",candidate_task="reformulate_previous_answer",needs_domain_pipeline=False)
    if _matches(t,FOLLOWUP_PATTERNS):return InteractionResult(InteractionType.FOLLOW_UP,0.95,referential_target="recent_assistant_concept",candidate_task="explain_or_resolve_previous_concept",needs_domain_pipeline=True)
    if _matches(t,TASK_CHANGE_PATTERNS):return InteractionResult(InteractionType.TASK_CHANGE,0.94,candidate_task="change_active_task",needs_domain_pipeline=True)
    if state and state.pending_clarifications and not _looks_like_explicit_question(t):
        words=t.split()
        if SHORT_CONFIRM.match(t) or (len(words)<=8 and len(t)<=100):return InteractionResult(InteractionType.CLARIFICATION_RESPONSE,0.92,referential_target=state.pending_clarifications[0].field,candidate_task="resolve_pending_clarification",needs_domain_pipeline=True)
    if re.search(r"\b(upload|review|check|analyse|analyze)\b.*\b(sop|proposal|document|form e|application|risk assessment)\b",t,re.I):return InteractionResult(InteractionType.DOCUMENT_WORKFLOW,0.94,candidate_task="document_workflow",needs_domain_pipeline=True)
    return InteractionResult(InteractionType.NEW_TASK,0.80,candidate_task="domain_question",needs_domain_pipeline=True)
