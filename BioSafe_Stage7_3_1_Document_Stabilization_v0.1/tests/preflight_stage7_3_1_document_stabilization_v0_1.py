#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from document_context_evidence_filter_v0_1 import filter_document_review_evidence
from researcher_ibc_boundary_guard_v0_1 import enforce_researcher_ibc_boundary
from compact_contradiction_renderer_v0_1 import build_compact_contradiction_fallback
from user_document_evidence_adapter_v0_1 import build_user_document_evidence
from critical_missing_compliance_guard_v0_1 import enforce_critical_missing_compliance_boundary

def main():
    # 1. LMO generic SOP review must allow zero RAG evidence if all candidates are wrong-domain.
    evidence = [
        {
            "evidence_id": "CLM-028",
            "document_id": "KB-MY-MOH2023",
            "claim_type": "transport_scope",
            "title": "Guidelines for Safe Transport of Clinical Specimens",
            "authority": "Ministry of Health Malaysia",
            "text": "Clinical-specimen transport guidance."
        },
    ]
    kept, audit = filter_document_review_evidence(
        "Identify vague statements in this SOP.",
        ["lmo_gmm_sop"],
        evidence,
    )
    assert kept == []
    assert audit["fallback_used"] is False
    assert audit["suppressed_evidence_ids"] == ["CLM-028"]

    # 2. Explicit transport intent should retain evidence.
    kept2, _ = filter_document_review_evidence(
        "How should this GMM be transported between facilities?",
        ["lmo_gmm_sop"],
        evidence,
    )
    assert [x["evidence_id"] for x in kept2] == ["CLM-028"]

    # 3. User document evidence gets DOC namespace.
    packet = {
        "structured_facts": [{
            "document_id": "SOP-03.txt",
            "jurisdiction_hint": "Malaysia",
            "facts": [{
                "field": "ppe",
                "source_span": "Use appropriate PPE."
            }]
        }],
        "missing_information": []
    }
    doc_ev = build_user_document_evidence(packet)
    assert doc_ev[0]["evidence_id"] == "DOC-1"
    assert doc_ev[0]["document_id"] == "SOP-03.txt"

    # 4. Researcher must not be told to submit IBC Assessment Report.
    sample = {
        "recommended_next_step": [
            "Submit the IBC Assessment Report for review."
        ]
    }
    repaired, changes = enforce_researcher_ibc_boundary(sample)
    assert changes
    assert "submit the ibc assessment report" not in " ".join(repaired["recommended_next_step"]).lower()

    # 5. Critical missing info must block permissive compliance wording.
    output = {
        "conclusion": "The project appears aligned with biosafety requirements under Malaysian law.",
        "recommended_next_step": []
    }
    policy = {"mode": "ASSESS_NOT_CERTIFY"}
    packet2 = {
        "missing_information": [
            {"field": "host_organism", "severity": "critical"}
        ]
    }
    repaired2, changes2 = enforce_critical_missing_compliance_boundary(
        output, policy, packet2
    )
    assert changes2
    assert "cannot determine or certify" in repaired2["conclusion"].lower()

    # 6. Contradiction fallback exact schema.
    packet3 = {
        "contradictions": [
            {
                "field": "project_duration",
                "value_a": "24 months",
                "value_b": "36 months",
                "status": "possible_value_conflict",
            }
        ]
    }
    fallback = build_compact_contradiction_fallback(packet3, evidence)
    expected = {
        "conclusion", "applicable_authority", "evidence",
        "missing_information", "recommended_next_step",
        "limitations", "safety"
    }
    assert set(fallback.keys()) == expected

    print("BioSafe Stage 7.3.1 preflight: PASS")
    print("Zero-evidence domain filter: PASS")
    print("User-document DOC evidence namespace: PASS")
    print("Researcher-vs-IBC boundary: PASS")
    print("Critical-missing compliance boundary: PASS")
    print("Schema-invalid contradiction fallback: PASS")

if __name__ == "__main__":
    main()
