
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path("/home/khengoon/biosafe")
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from integration_safety_gate_v0_1_2 import classify_safety
from policy_decision_guard_v0_3_3 import classify_policy
from biosafe_pipeline_v0_3_2 import BioSafePipelineV032

class BioSafeLocalService:
    def __init__(self, project_root: str | Path = PROJECT_ROOT):
        self.root = Path(project_root)
        self.pipeline = BioSafePipelineV032(root=self.root, top_k=3)

    def build_request(self, query: str, safety_class: str | None = None) -> dict[str, Any]:
        safety = classify_safety(query)
        policy = classify_policy(query)
        bundle, messages, *extra = self.pipeline.build_messages(
            query=query,
            safety_class=safety_class,
        )
        return {
            "query": query,
            "hard_safety": {
                "restricted": bool(getattr(safety, "restricted", False)),
                "reason": getattr(safety, "reason", ""),
                "matched": getattr(safety, "matched", []),
            },
            "policy": {
                "mode": getattr(policy, "mode", "STANDARD"),
                "constraints": getattr(policy, "constraints", []),
                "matched_rules": getattr(policy, "matched_rules", []),
            },
            "bundle": bundle,
            "messages": messages,
            "pipeline_extra": [str(x) for x in extra],
        }

    def run_query(self, query: str) -> dict[str, Any]:
        req = self.build_request(query)

        if req["hard_safety"]["restricted"]:
            return {
                "conclusion": "I can’t provide actionable assistance that increases harmful biological capability or bypasses containment.",
                "applicable_authority": [],
                "evidence": [],
                "missing_information": [],
                "recommended_next_step": [
                    "I can help with risk reduction, containment, biosafety controls, or high-level safety information instead."
                ],
                "limitations": [
                    "BioSafe does not provide actionable assistance that increases harmful biological capability or defeats containment."
                ],
                "safety": {
                    "classification": "refusal",
                    "response_mode": "refuse_and_redirect",
                    "reason": "restricted_biological_capability",
                },
                "_meta": req,
            }

        # Stage 9 v0.1 deliberately stops at the frozen message-construction boundary.
        # The installer also provides an adapter hook for the existing validated Live24 runtime.
        return {
            "conclusion": "BioSafe local shell is connected to the frozen request pipeline. Runtime inference adapter is ready to be wired to the validated Stage 8 execution path.",
            "applicable_authority": [],
            "evidence": [],
            "missing_information": [],
            "recommended_next_step": [],
            "limitations": [
                "Stage 9 v0.1 is a local product-shell integration package; it does not replace or modify the frozen inference components."
            ],
            "safety": {
                "classification": "normal",
                "response_mode": "answer",
                "reason": "",
            },
            "_meta": req,
        }
