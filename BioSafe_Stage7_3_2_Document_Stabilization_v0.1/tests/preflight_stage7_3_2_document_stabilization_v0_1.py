#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from document_evidence_alias_normalizer_v0_1 import normalize_document_evidence_aliases
from document_fact_precedence_guard_v0_1 import enforce_document_fact_precedence
from source_only_draft_renderer_v0_1 import build_source_only_draft_response

def main():
    evidence = [{
        "evidence_id": "DOC-1",
        "record_type": "user_document",
        "document_id": "PROP-02_Clinical_Specimen_Research_Proposal.txt",
        "text": "The proposal does not specify all specimen types."
    }]
    output = {"evidence": [{
        "evidence_id": "PROP-02_Clinical_Specimen_Research_Proposal.txt",
        "statement": "The proposal does not specify all specimen types."
    }]}
    repaired, changes = normalize_document_evidence_aliases(output, evidence)
    assert repaired["evidence"][0]["evidence_id"] == "DOC-1"
    assert changes

    packet = {"structured_facts": [{"facts": [{
        "source_span": "Specimens will be transferred using an approved courier."
    }]}]}
    output2 = {
        "conclusion": "Transport requires unapproved courier use.",
        "missing_information": [],
        "recommended_next_step": [],
        "limitations": []
    }
    repaired2, changes2 = enforce_document_fact_precedence(output2, packet)
    assert "unapproved courier" not in repaired2["conclusion"].lower()
    assert changes2

    packet3 = {"structured_facts": [{
        "document_type": "lmo_gmm_proposal",
        "normalized_profile": {
            "project_title": "Example Project",
            "principal_investigator": "Dr Example",
            "institution": "Example University",
            "project_duration": "24 months",
            "proposed_start": "January 2027",
            "objectives": None,
            "host_organism": None,
            "construct_identity": None,
            "facility": "Molecular Biology Laboratory",
            "culture_scale": None,
            "containment": None,
            "waste": "Collected through institutional system.",
            "transport": "May be transferred between laboratories.",
            "emergency_response": "Spills reported to PI.",
            "_status": {
                "project_title": "present",
                "principal_investigator": "present",
                "institution": "present",
                "project_duration": "present",
                "proposed_start": "present",
                "objectives": "missing",
                "host_organism": "explicitly_unclear",
                "construct_identity": "explicitly_unclear",
                "facility": "present",
                "culture_scale": "explicitly_unclear",
                "containment": "explicitly_unclear",
                "waste": "present",
                "transport": "present",
                "emergency_response": "present"
            }
        }
    }]}
    response = build_source_only_draft_response(packet3, evidence)
    assert response["conclusion"].startswith("The supported fields can be drafted")
    assert any("[Information not provided — confirmation required]" in x for x in response["missing_information"])

    print("BioSafe Stage 7.3.2 preflight: PASS")
    print("Document evidence alias normalizer: PASS")
    print("Document fact precedence guard: PASS")
    print("SOURCE_ONLY_DRAFT compact renderer: PASS")

if __name__ == "__main__":
    main()
