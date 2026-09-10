#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from user_document_evidence_adapter_v0_1 import build_user_document_evidence
from document_fact_precedence_guard_v0_1 import enforce_document_fact_precedence
from retrieved_claim_semantic_guard_v0_1 import enforce_retrieved_claim_semantic_consistency

def main():
    packet = {
        "structured_facts": [{
            "document_id": "PROP-02_Clinical_Specimen_Research_Proposal.txt",
            "document_type": "clinical_specimen_proposal",
            "jurisdiction_hint": "Malaysia",
            "facts": [],
            "normalized_profile": {
                "project_title": "Molecular analysis of archived clinical specimens.",
                "objectives": "Extract nucleic acids and analyse markers.",
                "transport": "Specimens will be transferred using an approved courier. Packaging and labelling will follow applicable requirements.",
                "waste": "Residual specimens and contaminated consumables will be disposed of as clinical waste.",
                "emergency_response": "Any spill, exposure or transport incident will be reported to the PI."
            }
        }]
    }

    doc_ev = build_user_document_evidence(packet, max_items=10)
    transport = [x for x in doc_ev if x.get("source_field") == "transport"]
    assert transport, "transport profile must become DOC evidence"
    assert "approved courier" in transport[0]["text"].lower()

    out = {
        "conclusion": "Transport requires unapproved courier use.",
        "missing_information": [],
        "recommended_next_step": [
            "Obtain formal approval from the Ministry of Health to classify specimens as infectious substances."
        ],
        "limitations": []
    }

    repaired, changes = enforce_document_fact_precedence(out, packet)
    assert "unapproved courier" not in repaired["conclusion"].lower()
    assert changes

    ev = [{
        "evidence_id": "CLM-028",
        "text": "The MOH clinical-specimen transport guideline does not serve as the clinical-waste guideline; clinical waste and chemical waste are outside its scope."
    }]
    out2 = {
        "conclusion": "The MOH guideline explicitly excludes clinical-specimen transport from its scope.",
        "missing_information": [],
        "recommended_next_step": [
            "Obtain formal approval from the Ministry of Health to classify specimens as infectious substances."
        ],
        "limitations": []
    }
    repaired2, changes2 = enforce_retrieved_claim_semantic_consistency(out2, ev)
    assert "excludes clinical-specimen transport" not in repaired2["conclusion"].lower()
    assert "formal approval from the ministry of health" not in " ".join(repaired2["recommended_next_step"]).lower()
    assert changes2

    print("BioSafe Stage 7.3.3 preflight: PASS")
    print("Normalized-profile DOC evidence: PASS")
    print("Approved-courier precedence: PASS")
    print("CLM-028 semantic consistency guard: PASS")
    print("Unsupported MOH classification-approval recommendation filter: PASS")

if __name__ == "__main__":
    main()
