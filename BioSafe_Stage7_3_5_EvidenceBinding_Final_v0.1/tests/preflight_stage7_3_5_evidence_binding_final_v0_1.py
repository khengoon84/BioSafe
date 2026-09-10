#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from user_document_evidence_adapter_v0_1 import build_user_document_evidence
from evidence_binding_guard_v0_1 import enforce_evidence_binding

def main():
    packet = {
        "structured_facts": [{
            "document_id": "PROP-02_Clinical_Specimen_Research_Proposal.txt",
            "document_type": "clinical_specimen_proposal",
            "jurisdiction_hint": "Malaysia",
            "facts": [],
            "normalized_profile": {
                "project_title": "Project title",
                "principal_investigator": "Dr Example",
                "institution": "Example Centre",
                "project_duration": "18 months",
                "proposed_start": "March 2027",
                "objectives": "Extract nucleic acids and analyse molecular markers.",
                "transport": "Specimens will be transferred using an approved courier.",
                "waste": "Residual specimens will be disposed of as clinical waste.",
                "emergency_response": "Incidents will be reported to the PI."
            }
        }]
    }

    doc_ev = build_user_document_evidence(packet, max_items=6)
    fields = [x.get("source_field") for x in doc_ev]
    assert fields[:4] == ["objectives", "transport", "waste", "emergency_response"], fields

    evidence_bundle = [
        {
            "evidence_id": "CLM-028",
            "record_type": "claim",
            "authority": "Ministry of Health Malaysia",
            "text": "Clinical waste and chemical waste are outside the transport guideline scope."
        },
        *doc_ev
    ]

    output = {
        "conclusion": "Activity-specific activity-specific risk assessment is needed.",
        "applicable_authority": ["Malaysia Ministry of Health Malaysia", "WHO Laboratory Biosafety Manual"],
        "evidence": [
            {
                "evidence_id": "DOC-1",
                "statement": "Wrong statement attached to DOC-1."
            },
            {
                "evidence_id": "CLM-028",
                "statement": "Wrong paraphrase."
            }
        ],
        "missing_information": [
            "Activity-specific activity-specific risk assessment."
        ],
        "recommended_next_step": [
            "Draft an activity-specific activity-specific risk assessment."
        ],
        "limitations": []
    }

    repaired, changes = enforce_evidence_binding(output, evidence_bundle)
    registry = {x["evidence_id"]: x for x in evidence_bundle}

    for e in repaired["evidence"]:
        assert e["statement"] == registry[e["evidence_id"]]["text"]

    assert repaired["applicable_authority"] == ["Ministry of Health Malaysia"]

    blob = " ".join([
        repaired["conclusion"],
        *repaired["missing_information"],
        *repaired["recommended_next_step"]
    ]).lower()
    assert "activity-specific activity-specific" not in blob
    assert changes

    print("BioSafe Stage 7.3.5 preflight: PASS")
    print("Substantive DOC evidence ordering: PASS")
    print("Evidence ID-to-statement binding: PASS")
    print("Authority grounding: PASS")
    print("Duplicate repair wording cleanup: PASS")

if __name__ == "__main__":
    main()
