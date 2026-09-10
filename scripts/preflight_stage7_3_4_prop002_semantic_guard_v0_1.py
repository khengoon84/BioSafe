#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from clinical_proposal_semantic_guard_v0_1 import enforce_clinical_proposal_semantic_guard

def main():
    packet = {
        "structured_facts": [{
            "document_type": "clinical_specimen_proposal",
            "normalized_profile": {
                "transport": "Specimens will be transferred using an approved courier."
            }
        }]
    }

    output = {
        "conclusion": (
            "The proposal contains three critical biosafety weaknesses: specimens may violate "
            "transport rules if not properly classified as Category A/B; waste creates a gap in "
            "regulatory compliance; and risk assessment matrices are absent."
        ),
        "missing_information": [
            "Activity-specific risk assessment matrices for laboratory personnel."
        ],
        "recommended_next_step": [
            "Draft an activity-specific risk assessment matrix.",
            "Obtain formal regulatory approval for the proposed transport classification and waste management procedures."
        ],
        "limitations": []
    }

    repaired, changes = enforce_clinical_proposal_semantic_guard(output, packet, [])

    blob = " ".join([
        repaired["conclusion"],
        *repaired["missing_information"],
        *repaired["recommended_next_step"]
    ]).lower()

    assert "critical biosafety weaknesses" not in blob
    assert "classified as category a/b" not in blob
    assert "risk assessment matrix" not in blob
    assert "gap in regulatory compliance" not in blob
    assert "obtain formal regulatory approval" not in blob
    assert changes

    print("BioSafe Stage 7.3.4 preflight: PASS")
    print("Category A/B uncertainty guard: PASS")
    print("Risk-assessment wording guard: PASS")
    print("Unsupported compliance-severity wording guard: PASS")
    print("Unsupported formal-approval recommendation guard: PASS")

if __name__ == "__main__":
    main()
