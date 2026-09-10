
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

@dataclass(frozen=True)
class EvidencePlan:
    intent: str
    retrieval_mode: str
    retrieval_required: bool
    authority_scope: str
    max_evidence: int
    rationale: str

class EvidenceRequirementPlanner:
    """
    Decide whether and what to retrieve BEFORE generation.

    Core invariant:
    Retrieve evidence according to the decision being made, not merely because
    a knowledge base exists.

    This planner does not alter regulatory/safety decisions and does not edit
    the frozen retriever. It controls retrieval activation for Unified Ask.
    """

    def plan(self, intent: str, query: str, *, attachments_present: bool=False,
             case_state: Optional[Dict[str, Any]]=None) -> EvidencePlan:
        intent = intent or "simple_answer"
        q = (query or "").strip().lower()

        if intent == "product_help":
            return EvidencePlan(intent, "none", False, "none", 0,
                                "Product identity/help does not require biosafety RAG.")

        if intent == "simple_answer":
            return EvidencePlan(intent, "none", False, "none", 0,
                                "Conversational/simple answer does not require authoritative retrieval by default.")

        if intent == "follow_up":
            return EvidencePlan(intent, "context_only", False, "conversation", 0,
                                "Follow-up should first use resolved conversation context; retrieval is replanned only if the resolved task requires it.")

        if intent == "educational_answer":
            # Definitions and foundational explanations should use general guidance,
            # not Malaysian regulatory claims, unless the user explicitly asks law/regulation.
            regulatory_terms = (
                "law","regulation","regulatory","act 678","biosafety act",
                "notification","notify","approval","compliance","required by"
            )
            if any(x in q for x in regulatory_terms):
                return EvidencePlan(intent, "regulatory", True, "jurisdiction_and_authority", 3,
                                    "Educational question explicitly asks a regulatory/legal dimension.")
            return EvidencePlan(intent, "general_guidance", True, "international_or_foundational", 2,
                                "Foundational explanation may use concise authoritative guidance; regulatory sources are not activated by default.")

        if intent == "regulatory_assessment":
            return EvidencePlan(intent, "regulatory", True, "jurisdiction_and_authority", 3,
                                "Regulatory applicability/conclusion requires authoritative regulatory evidence.")

        if intent == "document_review":
            return EvidencePlan(intent, "document_plus_authority", True, "task_relevant_authority", 3,
                                "Review uses user document as scenario evidence plus relevant authority.")

        if intent == "form_e_assist":
            return EvidencePlan(intent, "form_e_regulatory", True, "malaysia_form_e_and_applicable_regulation", 3,
                                "Form E assistance requires project facts plus Malaysian Form E/regulatory evidence.")

        if intent == "safety_redirect":
            return EvidencePlan(intent, "safe_guidance_only", False, "none", 0,
                                "Safety gate controls response; retrieve safe governance guidance only when separately justified.")

        return EvidencePlan(intent, "none", False, "none", 0,
                            "No evidence requirement established.")

    def as_dict(self, *args, **kwargs):
        return asdict(self.plan(*args, **kwargs))
