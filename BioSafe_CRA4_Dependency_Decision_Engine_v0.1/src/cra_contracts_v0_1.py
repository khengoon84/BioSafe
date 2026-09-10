from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from enum import Enum
import json

class InteractionType(str, Enum):
    SOCIAL="SOCIAL"
    PRODUCT_HELP="PRODUCT_HELP"
    NEW_TASK="NEW_TASK"
    CLARIFICATION_RESPONSE="CLARIFICATION_RESPONSE"
    FOLLOW_UP="FOLLOW_UP"
    REFORMULATE="REFORMULATE"
    TASK_CHANGE="TASK_CHANGE"
    DOCUMENT_WORKFLOW="DOCUMENT_WORKFLOW"

class FactStatus(str, Enum):
    UNKNOWN="unknown"
    USER_ASSERTED="user_asserted"
    USER_CONFIRMED="user_confirmed"
    DOCUMENT_EXTRACTED="document_extracted"
    AUTHORITY_DERIVED="authority_derived"
    INFERRED="inferred"
    DISPUTED="disputed"

class DecisionStatus(str, Enum):
    SUPPORTED="supported"
    NOT_SUPPORTED="not_supported"
    INSUFFICIENT_INFORMATION="insufficient_information"
    NOT_APPLICABLE="not_applicable"
    CONFLICTING_EVIDENCE="conflicting_evidence"
    REQUIRES_HUMAN_REVIEW="requires_human_review"

class ResponseType(str, Enum):
    PRODUCT_HELP="product_help"
    SIMPLE_ANSWER="simple_answer"
    EDUCATIONAL_ANSWER="educational_answer"
    NEEDS_CLARIFICATION="needs_clarification"
    REGULATORY_ASSESSMENT="regulatory_assessment"
    DOCUMENT_REVIEW="document_review"
    FORM_E_ASSIST="form_e_assist"
    SAFETY_REDIRECT="safety_redirect"

@dataclass
class InteractionResult:
    interaction_type: InteractionType
    confidence: float
    referential_target: Optional[str] = None
    candidate_task: Optional[str] = None
    needs_domain_pipeline: bool = True

@dataclass
class FactValue:
    value: Any = None
    status: FactStatus = FactStatus.UNKNOWN
    source: Optional[str] = None
    confidence: Optional[float] = None

@dataclass
class AssistantConcept:
    concept_id: str
    label: str
    turn_id: str

@dataclass
class PendingClarification:
    field: str
    question: str
    turn_id: str

@dataclass
class ConversationState:
    session_id: str
    current_topic: Optional[str] = None
    active_interaction: Optional[InteractionType] = None
    last_user_goal: Optional[str] = None
    recent_assistant_concepts: List[AssistantConcept] = field(default_factory=list)
    pending_clarifications: List[PendingClarification] = field(default_factory=list)
    unresolved_references: List[str] = field(default_factory=list)
    last_response_type: Optional[ResponseType] = None

@dataclass
class CaseState:
    case_id: str
    jurisdiction: FactValue = field(default_factory=FactValue)
    facts: Dict[str, FactValue] = field(default_factory=dict)
    active_domains: List[str] = field(default_factory=list)
    inactive_domains: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)

@dataclass
class TaskFrame:
    task_id: str
    interaction_type: InteractionType
    user_goal: str
    current_question: str
    jurisdiction: Optional[str] = None
    known_facts: List[str] = field(default_factory=list)
    relevant_unknowns: List[str] = field(default_factory=list)
    requested_domains: List[str] = field(default_factory=list)
    activated_domains: List[str] = field(default_factory=list)
    inactive_domains: List[str] = field(default_factory=list)
    decisions_requested: List[str] = field(default_factory=list)
    decisions_not_requested: List[str] = field(default_factory=list)
    response_expectations: List[str] = field(default_factory=list)

@dataclass
class EvidencePlan:
    skip_rag: bool
    required_domains: List[str] = field(default_factory=list)
    required_evidence_types: List[str] = field(default_factory=list)
    preferred_authority_tiers: List[int] = field(default_factory=list)
    exclude_domains: List[str] = field(default_factory=list)
    jurisdiction: Optional[str] = None

@dataclass
class PrerequisiteResult:
    name: str
    satisfied: bool
    fact_refs: List[str] = field(default_factory=list)

@dataclass
class DecisionNode:
    decision_id: str
    decision_type: str
    status: DecisionStatus
    prerequisites: List[PrerequisiteResult] = field(default_factory=list)
    authority_refs: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
    unresolved_dependencies: List[str] = field(default_factory=list)
    reason: str = ""

@dataclass
class VerificationResult:
    decision: str
    checks: Dict[str, bool]
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class ResponsePlan:
    response_type: ResponseType
    direct_answer: str
    why_this_matters: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    recommended_next_steps: List[str] = field(default_factory=list)
    source_refs: List[str] = field(default_factory=list)
    show_sources_collapsed: bool = True

def to_dict(obj):
    def convert(v):
        if isinstance(v, Enum):
            return v.value
        if hasattr(v, "__dataclass_fields__"):
            return {k: convert(val) for k, val in asdict(v).items()}
        if isinstance(v, dict):
            return {k: convert(val) for k, val in v.items()}
        if isinstance(v, list):
            return [convert(x) for x in v]
        return v
    return convert(obj)

def to_json(obj, *, indent=2):
    return json.dumps(to_dict(obj), indent=indent, ensure_ascii=False)
