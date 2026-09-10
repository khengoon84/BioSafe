#!/usr/bin/env python3
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from context_budget_manager_v0_1 import select_profile, response_contract
from deterministic_response_assembler_v0_1 import assemble_biosafe_response
from compact_reasoning_recovery_v0_1 import recover_compact_reasoning

def main():
    lite = select_profile("qwen3.5:0.8b")
    standard = select_profile("qwen3.5:2b")
    assert lite.output_token_budget == 420
    assert lite.max_missing_findings == 3
    assert lite.max_recommendations == 2
    assert lite.max_limitations == 1
    assert standard.output_token_budget == 900

    contract = response_contract(lite).lower()
    assert "only conclusion, missing_information, and recommended_next_step" in contract
    assert "do not generate applicable_authority" in contract

    bundle = {
        "policy_decision": {"mode": "STANDARD"},
        "evidence_bundle": [
            {
                "evidence_id": "CLM-026",
                "record_type": "claim",
                "authority": "Ministry of Health Malaysia",
                "text": "MOH transport guidance covers classification and packaging/labelling/marking requirements."
            },
            {
                "evidence_id": "DOC-1",
                "record_type": "user_document",
                "authority": "User-supplied document",
                "text": "Specimens will be transferred using an approved courier."
            }
        ]
    }
    compact = {
        "conclusion": "The proposal needs clarification before a defensible assessment.",
        "missing_information": ["Specimen infectious status.", "Transport classification."],
        "recommended_next_step": ["Confirm classification using applicable guidance."]
    }
    assembled = assemble_biosafe_response(compact, bundle)
    assert set(assembled) == {
        "conclusion", "applicable_authority", "evidence",
        "missing_information", "recommended_next_step",
        "limitations", "safety"
    }
    assert assembled["applicable_authority"] == ["Ministry of Health Malaysia"]
    assert assembled["evidence"][0]["evidence_id"] == "CLM-026"
    assert assembled["safety"]["classification"] == "caution"

    raw = json.dumps(compact)
    recovered, valid, err = recover_compact_reasoning(raw)
    assert valid is True and recovered == compact

    truncated = (
        '{"conclusion":"Needs clarification.",'
        '"missing_information":["Specimen status."],'
        '"recommended_next_step":["Confirm classification."]'
    )
    recovered2, valid2, err2 = recover_compact_reasoning(truncated)
    assert valid2 is False
    assert recovered2["conclusion"] == "Needs clarification."
    assert recovered2["missing_information"] == ["Specimen status."]
    assert recovered2["recommended_next_step"] == ["Confirm classification."]

    print("BioSafe Context Budget Manager v0.2 preflight: PASS")
    print("Lite compact-generation envelope: PASS")
    print("Standard profile preservation: PASS")
    print("Three-field Qwen response contract: PASS")
    print("Deterministic response assembler: PASS")
    print("Canonical authority/evidence assembly: PASS")
    print("Deterministic safety/limitation assembly: PASS")
    print("Compact reasoning recovery: PASS")

if __name__ == "__main__":
    main()
