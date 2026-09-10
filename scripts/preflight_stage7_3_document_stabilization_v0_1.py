#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from document_context_evidence_filter_v0_1 import filter_document_review_evidence
from researcher_ibc_boundary_guard_v0_1 import enforce_researcher_ibc_boundary
from compact_contradiction_renderer_v0_1 import build_compact_contradiction_fallback

def main():
    # 1. LMO generic SOP review should suppress clinical-transport evidence.
    evidence = [
        {
            "evidence_id": "CLM-028",
            "document_id": "KB-MY-MOH2023",
            "claim_type": "transport_scope",
            "title": "Guidelines for Safe Transport of Clinical Specimens",
            "authority": "Ministry of Health Malaysia",
            "text": "Clinical-specimen transport guidance."
        },
        {
            "evidence_id": "CLM-014",
            "document_id": "KB-MY-GMMRA",
            "claim_type": "risk_assessment",
            "title": "GMM Risk Assessment Guideline",
            "authority": "Department of Biosafety / Malaysia",
            "text": "Risk assessment should be reviewed."
        },
    ]
    kept, audit = filter_document_review_evidence(
        "Identify vague statements in this SOP.",
        ["lmo_gmm_sop"],
        evidence,
    )
    assert [x["evidence_id"] for x in kept] == ["CLM-014"]
    assert "CLM-028" in audit["suppressed_evidence_ids"]

    # Explicit transport question should retain the transport evidence.
    kept2, _ = filter_document_review_evidence(
        "How should this GMM be transported between facilities?",
        ["lmo_gmm_sop"],
        evidence,
    )
    assert "CLM-028" in [x["evidence_id"] for x in kept2]

    # 2. Researcher must not be told to submit IBC Assessment Report.
    sample = {
        "recommended_next_step": [
            "Provide the host organism details.",
            "Submit the IBC Assessment Report for review by the registered IBC.",
        ]
    }
    repaired, changes = enforce_researcher_ibc_boundary(sample)
    assert changes
    joined = " ".join(repaired["recommended_next_step"]).lower()
    assert "submit the ibc assessment report" not in joined
    assert "ibc-only" in joined

    # 3. Contradiction fallback must produce concise exact BioSafe schema.
    packet = {
        "contradictions": [
            {
                "field": "project_duration",
                "value_a": "24 months",
                "value_b": "36 months",
                "status": "possible_value_conflict",
            },
            {
                "field": "host_organism",
                "value_a": None,
                "value_b": "Escherichia coli K-12",
                "finding_type": "unsupported_secondary_detail",
            },
        ]
    }
    fallback = build_compact_contradiction_fallback(packet, evidence)
    expected = {
        "conclusion", "applicable_authority", "evidence",
        "missing_information", "recommended_next_step",
        "limitations", "safety"
    }
    assert set(fallback.keys()) == expected
    assert len(fallback["missing_information"]) <= 7
    assert "24 months" in fallback["missing_information"][0]
    assert "36 months" in fallback["missing_information"][0]

    print("BioSafe Stage 7.3 preflight: PASS")
    print("LMO evidence filter: PASS")
    print("Researcher-vs-IBC boundary: PASS")
    print("Compact contradiction fallback: PASS")

if __name__ == "__main__":
    main()
