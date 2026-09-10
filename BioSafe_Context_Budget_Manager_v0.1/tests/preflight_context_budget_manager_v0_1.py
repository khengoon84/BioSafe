#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"src"))

from context_budget_manager_v0_1 import (
    select_profile, estimate_tokens, budget_evidence,
    compact_packet_for_budget, response_contract, audit_prompt
)
from response_budget_guard_v0_1 import enforce_response_budget

def main():
    lite = select_profile("qwen3.5:0.8b")
    standard = select_profile("qwen3.5:2b")
    assert lite.profile_id == "qwen3.5-lite"
    assert standard.profile_id == "qwen3.5-standard"
    assert lite.target_prompt_tokens < standard.target_prompt_tokens
    assert lite.output_token_budget < standard.output_token_budget

    evidence = [
        *[{"evidence_id": f"CLM-{i}", "record_type": "claim"} for i in range(1, 6)],
        *[{"evidence_id": f"DOC-{i}", "record_type": "user_document"} for i in range(1, 9)],
    ]
    selected, audit = budget_evidence(evidence, lite)
    assert len([x for x in selected if x["record_type"] == "claim"]) == 3
    assert len([x for x in selected if x["record_type"] == "user_document"]) == 6
    assert audit["dropped_ids"]

    packet = {
        "missing_information": list(range(10)),
        "contradictions": list(range(12)),
        "structured_facts": [{
            "missing_fields": list(range(10)),
            "contradictions": list(range(12))
        }]
    }
    compact = compact_packet_for_budget(packet, lite)
    assert len(compact["missing_information"]) == 6
    assert len(compact["contradictions"]) == 7
    assert len(compact["structured_facts"][0]["missing_fields"]) == 6

    output = {
        "conclusion": " ".join(["word"] * 120),
        "evidence": list(range(10)),
        "missing_information": list(range(10)),
        "recommended_next_step": list(range(8)),
        "limitations": list(range(5)),
    }
    repaired, changes = enforce_response_budget(
        output, 6, 3, 2, 6
    )
    assert len(repaired["conclusion"].split()) <= 90
    assert len(repaired["recommended_next_step"]) == 3
    assert changes

    assert estimate_tokens("x" * 4000) == 1000
    contract = response_contract(lite)
    assert "exactly one complete json object" in contract.lower()

    messages = [{"role": "user", "content": "x" * 4000}]
    pa = audit_prompt("qwen3.5:0.8b", messages, audit)
    assert pa["estimated_prompt_tokens"] == 1000
    assert pa["within_target"] is True

    print("BioSafe Context Budget Manager v0.1 preflight: PASS")
    print("Model-specific Lite/Standard profiles: PASS")
    print("Evidence budgeting: PASS")
    print("Structured-finding compaction: PASS")
    print("Response budget contract: PASS")
    print("Post-generation response cap: PASS")
    print("Prompt budget audit: PASS")

if __name__ == "__main__":
    main()
