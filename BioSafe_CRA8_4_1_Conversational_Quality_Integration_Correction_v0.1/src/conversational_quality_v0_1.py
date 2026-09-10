from __future__ import annotations
import re
from typing import Any, Dict, Optional, Tuple

INTERNAL_LEAK_PATTERNS=(
    "does not require a new regulatory retrieval",
    "conversation_local",
    "retrieval skipped",
)

# Small, authoritative concept cards are deterministic product knowledge, not model improvisation.
# They are deliberately limited to stable foundational concepts already represented in BioSafe KB v0.2.
CONCEPT_CARDS={
    "biosafety_vs_biosecurity": {
        "direct_answer": (
            "Laboratory biosafety uses containment principles, technologies and practices to prevent "
            "unintentional exposure to biological agents or their accidental release. Laboratory biosecurity "
            "uses protection, control and accountability measures to prevent unauthorized access, loss, theft, "
            "misuse, diversion or intentional release of biological materials and related assets or information. "
            "In short: biosafety primarily addresses accidental harm; biosecurity primarily addresses deliberate "
            "or unauthorized misuse. Many laboratory activities need both, based on risk assessment."
        ),
        "applicable_authority":["World Health Organization"],
        "evidence":[
            {"evidence_id":"KB-WHO-LBM4","statement":"WHO Laboratory Biosafety Manual, 4th ed. (2020): risk- and evidence-based laboratory biosafety."},
            {"evidence_id":"KB-WHO-BIOSEC","statement":"WHO Laboratory Biosecurity Guidance (2024): biosecurity risk management for biological material, technology and information."},
        ],
        "missing_information":[],"recommended_next_step":[],
        "limitations":["This is a general explanation. Specific legal or institutional requirements depend on the activity and jurisdiction."],
        "safety":{"classification":"normal","response_mode":"answer","reason":"Foundational educational explanation."},
    },
    "biosafety_biosecurity_applicability": {
        "direct_answer": (
            "Whether you need biosafety measures, biosecurity measures, or both depends on the activity and its risks. "
            "Biosafety is relevant when work could expose people or the environment to biological hazards or cause an accidental release. "
            "Biosecurity becomes relevant when biological materials, technology, equipment, data or know-how could be lost, stolen, accessed without authorization, diverted or misused. "
            "Many research activities require both. A risk assessment should identify the hazards, possible accidental exposures or releases, and credible security or misuse concerns before controls are selected."
        ),
        "applicable_authority":["World Health Organization"],
        "evidence":[
            {"evidence_id":"KB-WHO-LBM4","statement":"WHO LBM4 uses risk assessment to determine proportionate biosafety controls."},
            {"evidence_id":"KB-WHO-BIOSEC","statement":"WHO 2024 guidance applies a risk- and consequence-based approach to laboratory biosecurity."},
        ],
        "missing_information":[],
        "recommended_next_step":["If you want an activity-specific assessment, describe the biological material, what you plan to do with it, where the work will occur, and any genetic modification involved."],
        "limitations":["This does not determine whether a particular Malaysian law, institutional rule or approval applies until the relevant activity facts are known."],
        "safety":{"classification":"normal","response_mode":"answer","reason":"General applicability framework; no compliance determination requested."},
    },
    "bacillus_anthracis_general": {
        "direct_answer": (
            "If you mean Bacillus anthracis: yes. It is the bacterium that causes anthrax, a serious infectious disease. "
            "The risk in a laboratory depends on factors such as the material being handled, its viability and concentration, the procedure, the potential exposure route, and the controls in place. "
            "Its presence alone does not establish which Malaysian regulatory notification pathway applies; that requires the relevant regulatory trigger facts."
        ),
        "applicable_authority":["World Health Organization"],
        "evidence":[],
        "missing_information":[],
        "recommended_next_step":["If you are asking about a specific laboratory activity, describe the material and the planned procedure so BioSafe can assess the relevant biosafety considerations without assuming regulatory applicability."],
        "limitations":["This is a high-level hazard explanation, not an organism-specific containment or regulatory determination."],
        "safety":{"classification":"caution","response_mode":"answer","reason":"High-level hazard information only; no operational handling instructions."},
    },
}

def normalize_likely_entity(text:str)->Tuple[str,Optional[str]]:
    q=text or ""
    # Conservative high-confidence typo aliases only. Never silently changes a different genus/species.
    patterns=[r"\bbacillus\s+antracts\b",r"\bbacillus\s+anthrasis\b",r"\bbacillus\s+antracis\b"]
    for p in patterns:
        if re.search(p,q,re.I):
            return re.sub(p,"Bacillus anthracis",q,flags=re.I),"Bacillus anthracis"
    return q,None

def detect_foundational_intent(text:str)->Optional[str]:
    t=(text or "").strip().lower()
    if ("biosafety" in t and "biosecurity" in t and
        re.search(r"\b(difference|different|versus|vs\.?|what is|what's)\b",t)):
        return "biosafety_vs_biosecurity"
    if "biosafety" in t and "biosecurity" in t and re.search(r"\b(comply|need|apply|both|which)\b",t):
        return "biosafety_biosecurity_applicability"
    return None

def detect_entity_card(text:str)->Optional[str]:
    t=(text or "").lower()
    if "bacillus anthracis" in t and re.search(r"\b(dangerous|hazard|harmful|risk|cause)\b",t):
        return "bacillus_anthracis_general"
    return None

def is_elaboration_request(text:str)->bool:
    t=(text or "").strip().lower()
    return bool(re.match(r"^(please\s+)?(elaborate|explain(?:\s+(?:more|further))?|tell me more|i do not understand|i don't understand)(?:[.!?].*)?$",t))

def elaborate_previous_response(last_response:Dict[str,Any])->Optional[Dict[str,Any]]:
    if not isinstance(last_response,dict): return None
    base=(last_response.get("direct_answer") or last_response.get("conclusion") or "").strip()
    if not base or any(p in base.lower() for p in INTERNAL_LEAK_PATTERNS): return None
    out=dict(last_response)
    # Do not fabricate new facts. Re-present the prior supported answer and make the relationship explicit.
    out["direct_answer"]=(
        base + "\n\nPut another way, the important point is to separate the inherent hazard from the "
        "risk of the specific activity. Hazard tells you what harm the agent or material can cause; risk depends on "
        "how the work is performed, possible exposure or release routes, and the controls in place."
    )
    return out

def sanitize_user_response(response:Dict[str,Any], *, response_type:Optional[str]=None)->Dict[str,Any]:
    r=dict(response or {})
    answer=(r.get("direct_answer") or r.get("conclusion") or "")
    if any(p in str(answer).lower() for p in INTERNAL_LEAK_PATTERNS):
        r["direct_answer"]="I need a little more context to answer that accurately. Please tell me which part of the previous answer you want me to explain."
        r.pop("conclusion",None)
    # Educational/simple answers should not invent user-specific compliance gaps.
    if response_type in {"educational_answer","simple_answer"}:
        r["missing_information"]=[]
    return r
