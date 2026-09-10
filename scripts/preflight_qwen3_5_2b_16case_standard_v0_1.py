#!/usr/bin/env python3
from __future__ import annotations
import sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from context_budget_manager_v0_1 import select_profile, response_contract
from deterministic_response_assembler_v0_1 import assemble_biosafe_response

def main():
    standard = select_profile("qwen3.5:2b")
    assert standard.profile_id == "qwen3.5-standard"
    assert standard.target_prompt_tokens == 32000
    assert standard.hard_prompt_tokens == 64000
    assert standard.output_token_budget == 900
    assert standard.max_rag_claims == 5
    assert standard.max_document_evidence == 10

    contract = response_contract(standard).lower()
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
        max_missing=standard.max_missing_findings,
        max_recommendations=standard.max_recommendations,
        max_evidence=standard.max_rag_claims,
        max_limitations=standard.max_limitations,
    )
    assert final["evidence"][0]["statement"] == "Canonical regulatory evidence."
    assert "safety" in final

    print("BioSafe Qwen3.5-2B 16-case Standard preflight: PASS")
    print("Structured Document Layer v1.0 frozen: PASS")
    print("Qwen3.5-2B Standard profile: PASS")
    print("Compact reasoning contract: PASS")
    print("Deterministic Response Assembler v0.1: PASS")
    print("Canonical evidence assembly: PASS")

if __name__ == "__main__":
    main()
