
from __future__ import annotations
import json

def build_llm_user_message(original_query: str, packet: dict) -> str:
    return (
        original_query.strip()
        + "\n\n--- STRUCTURED DOCUMENT ANALYSIS (deterministic pre-processing) ---\n"
        + json.dumps(packet, indent=2, ensure_ascii=False)
        + "\n--- END STRUCTURED DOCUMENT ANALYSIS ---"
    )
