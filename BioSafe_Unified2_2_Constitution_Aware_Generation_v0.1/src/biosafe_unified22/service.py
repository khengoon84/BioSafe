
from __future__ import annotations
from pathlib import Path
import sys

ROOT = Path("/home/khengoon/biosafe")
for p in (ROOT, ROOT/"src", ROOT/"unified_v1"/"src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import full_inference_service_v0_1 as frozen
from biosafe_unified22 import load_constitution, augment_compact_messages

class BioSafeConstitutionAwareInferenceServiceV01(frozen.BioSafeFullInferenceServiceV011):
    """
    Experimental Unified-2.2 service.
    It reuses the frozen inference pipeline and temporarily intercepts only the
    compact generation-message construction to add:
      - Behavioral Constitution in role=system
      - interaction/case context in role=user structured payload
    Retrieval query and frozen post-generation guards remain unchanged.
    """
    def __init__(self, project_root: str | Path = ROOT):
        super().__init__(project_root)
        self.constitution = load_constitution()
        self._interaction_context = {}

    def infer(self, query: str, documents=None, workflow: str="ask", interaction_context=None):
        self._interaction_context = interaction_context or {}
        original_compact = frozen._compact_messages

        def constitution_compact(base_messages, q, bundle, packet, policy, profile, wf):
            base = original_compact(base_messages, q, bundle, packet, policy, profile, wf)
            enriched = augment_compact_messages(
                base,
                constitution=self.constitution,
                interaction_context=self._interaction_context,
            )
            return enriched

        frozen._compact_messages = constitution_compact
        try:
            result = super().infer(query, documents=documents, workflow=workflow)
        finally:
            frozen._compact_messages = original_compact

        if isinstance(result, dict):
            result.setdefault("_meta", {})
            result["_meta"]["unified22_constitution"] = True
            result["_meta"]["unified22_clean_query"] = query
        return result
