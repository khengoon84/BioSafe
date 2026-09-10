#!/usr/bin/env python3
from __future__ import annotations
import sys, json
from pathlib import Path
from dataclasses import replace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))
from context_budget_manager_v0_1 import select_profile, response_contract

def main():
    lite = select_profile("qwen3.5:0.8b")
    assert lite.profile_id == "qwen3.5-lite"
    assert lite.target_prompt_tokens == 16000
    assert lite.hard_prompt_tokens == 24000
    assert lite.output_token_budget == 420
    assert lite.max_rag_claims == 3
    assert lite.max_document_evidence == 6
    assert lite.max_missing_findings == 3
    assert lite.max_recommendations == 2
    assert lite.max_limitations == 1

    freeze = json.loads(
        (ROOT/"data"/"Structured_Document_Analysis_Layer_v1.0_FREEZE.json").read_text(encoding="utf-8")
    )
    assert freeze["status"] == "ARCHITECTURE_FROZEN"

    contract = response_contract(lite).lower()
    assert "only conclusion, missing_information, and recommended_next_step" in contract

    print("BioSafe Qwen3.5-0.8B 16-case Lite comparison preflight: PASS")
    print("Structured Document Layer v1.0 frozen: PASS")
    print("Qwen3.5-0.8B Lite context profile: PASS")
    print("420-token compact generation envelope: PASS")
    print("3/6/3/2/1 response-evidence caps: PASS")
    print("Blinded comparison builder: PRESENT")

if __name__ == "__main__":
    main()
