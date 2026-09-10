
from __future__ import annotations
import re

TYPE_RULES = [
    ("form_e_completed", [r"\bform e\b", r"\bsection a[1-6]\b"]),
    ("lmo_gmm_proposal", [r"\bproposal\b", r"\b(lmo|gmm|genetically modified)\b"]),
    ("clinical_specimen_proposal", [r"\bproposal\b", r"\bclinical specimen"]),
    ("lmo_gmm_sop", [r"\bsop\b", r"\b(lmo|gmm|genetically modified)\b"]),
    ("clinical_specimen_sop", [r"\bsop\b", r"\bclinical specimen"]),
    ("biological_waste_sop", [r"\bsop\b", r"\b(biological|clinical)\s+waste\b"]),
]

def classify_document(text: str) -> dict:
    low = text.lower()
    scored = []
    for doc_type, patterns in TYPE_RULES:
        score = sum(1 for p in patterns if re.search(p, low, flags=re.I))
        if score:
            scored.append((score, doc_type))
    scored.sort(reverse=True)
    if not scored:
        return {"document_type": "unknown", "confidence": 0.25}
    top_score, top_type = scored[0]
    conf = min(0.95, 0.45 + 0.2 * top_score)
    return {"document_type": top_type, "confidence": round(conf, 2)}
