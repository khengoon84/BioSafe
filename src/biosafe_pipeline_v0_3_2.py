#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import json

from biosafe_pipeline_v0_1 import BioSafePipelineV01
from policy_decision_guard_v0_3_2 import classify_policy, build_policy_instruction


class BioSafePipelineV032:
    def __init__(self, root: Path | str, top_k: int = 3):
        self.base = BioSafePipelineV01(root, top_k)
        self.root = Path(root)
        self.top_k = top_k

    def build_messages(self, query: str, case_id: str | None = None, safety_class: str | None = None):
        policy = classify_policy(query)

        if policy.short_circuit:
            bundle = self.base.build_bundle(query, case_id, safety_class)
            bundle["policy_decision"] = policy.to_dict()
            bundle["route"]["safety_sensitive"] = True
            bundle["route"]["domain"] = "SAFETY"
            bundle["route"]["intent"] = "deterministic_refusal"
            return bundle, [], policy.deterministic_response

        bundle, messages = self.base.build_messages(query, case_id, safety_class)
        bundle["policy_decision"] = policy.to_dict()

        if messages and len(messages) >= 2:
            payload = json.loads(messages[1]["content"])
            payload["policy_decision"] = policy.to_dict()
            payload["policy_instruction"] = build_policy_instruction(policy)
            messages[1]["content"] = json.dumps(payload, ensure_ascii=False, indent=2)

        return bundle, messages, None
