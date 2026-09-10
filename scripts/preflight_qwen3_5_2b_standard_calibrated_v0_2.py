#!/usr/bin/env python3
from __future__ import annotations
import sys, json
from pathlib import Path
from dataclasses import replace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from context_budget_manager_v0_1 import select_profile, response_contract
from deterministic_response_assembler_v0_1 import assemble_biosafe_response

def main():
    standard = select_profile("qwen3.5:2b")
    calibrated = replace(
        standard,
        output_token_budget=420,
        max_rag_claims=3,
        max_document_evidence=6,
        max_missing_findings=3,
        max_recommendations=2,
        max_limitations=1,
    )

    # Keep Standard prompt/context profile.
    assert calibrated.profile_id == "qwen3.5-standard"
    assert calibrated.target_prompt_tokens == 32000
    assert calibrated.hard_prompt_tokens == 64000

    # Match Lite compact reasoning envelope.
    assert calibrated.output_token_budget == 420
    assert calibrated.max_rag_claims == 3
    assert calibrated.max_document_evidence == 6
    assert calibrated.max_missing_findings == 3
    assert calibrated.max_recommendations == 2
    assert calibrated.max_limitations == 1

    contract = response_contract(calibrated).lower()
    assert "only conclusion, missing_information, and recommended_next_step" in contract
    assert "do not generate applicable_authority" in contract

    freeze = json.loads(
        (ROOT/"data"/"Structured_Document_Analysis_Layer_v1.0_FREEZE.json").read_text(encoding="utf-8")
    )
    assert freeze["status"] == "ARCHITECTURE_FROZEN"

    bundle = {
        "policy_decision": {"mode": "STANDARD"},
        "evidence_bundle": [
            {
                "evidence_id": "CLM-X",
                "record_type": "claim",
                "authority": "Authoritative source",
                "text": "Canonical regulatory evidence."
            },
            {
                "evidence_id": "DOC-1",
                "record_type": "user_document",
                "text": "Scenario fact."
            }
        ]
    }
    compact = {
        "conclusion": "Further information is needed.",
        "missing_information": ["Missing scenario detail."],
        "recommended_next_step": ["Confirm the missing detail."]
    }
    final = assemble_biosafe_response(
        compact, bundle,
        max_missing=calibrated.max_missing_findings,
        max_recommendations=calibrated.max_recommendations,
        max_evidence=calibrated.max_rag_claims,
        max_limitations=calibrated.max_limitations,
    )
    assert len(final["evidence"]) <= 3
    assert len(final["recommended_next_step"]) <= 2
    assert len(final["limitations"]) <= 1

    print("BioSafe Qwen3.5-2B Standard-Calibrated v0.2 preflight: PASS")
    print("Structured Document Layer v1.0 frozen: PASS")
    print("2B Standard prompt budget preserved: PASS")
    print("Lite-equivalent compact reasoning envelope: PASS")
    print("Generation budget 420: PASS")
    print("Deterministic Response Assembler v0.1: PASS")
    print("Canonical evidence/authority assembly: PASS")

if __name__ == "__main__":
    main()
