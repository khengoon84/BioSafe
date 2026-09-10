
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

@dataclass(frozen=True)
class ModelBudgetProfile:
    profile_id: str
    model_id: str
    target_prompt_tokens: int
    hard_prompt_tokens: int
    output_token_budget: int
    max_rag_claims: int
    max_document_evidence: int
    max_missing_findings: int
    max_contradictions: int
    max_recommendations: int
    max_limitations: int

PROFILES = {
    "qwen3.5-lite": ModelBudgetProfile(
        "qwen3.5-lite", "qwen3.5:0.8b",
        16000, 24000, 420, 3, 6, 3, 7, 2, 1
    ),
    "qwen3.5-standard": ModelBudgetProfile(
        "qwen3.5-standard", "qwen3.5:2b",
        32000, 64000, 900, 5, 10, 8, 10, 4, 3
    ),
}

def select_profile(model_id: str) -> ModelBudgetProfile:
    mid = (model_id or "").lower()
    if "qwen3.5:2b" in mid or "qwen3.5-2b" in mid:
        return PROFILES["qwen3.5-standard"]
    return PROFILES["qwen3.5-lite"]

def estimate_tokens(text: str) -> int:
    # Conservative dependency-free engineering estimate, not a tokenizer.
    return max(1, (len(text or "") + 3) // 4)

def budget_evidence(evidence_bundle: list[dict[str, Any]], profile: ModelBudgetProfile):
    docs = [e for e in (evidence_bundle or []) if e.get("record_type") == "user_document"]
    rag = [e for e in (evidence_bundle or []) if e.get("record_type") != "user_document"]

    # Preserve upstream order: CFG-02 ranking and substantive DOC ordering are frozen.
    selected_rag = rag[:profile.max_rag_claims]
    selected_docs = docs[:profile.max_document_evidence]
    selected = selected_rag + selected_docs
    selected_ids = {e.get("evidence_id") for e in selected}

    audit = {
        "profile_id": profile.profile_id,
        "original_count": len(evidence_bundle or []),
        "selected_count": len(selected),
        "selected_ids": [e.get("evidence_id") for e in selected],
        "dropped_ids": [
            e.get("evidence_id") for e in (evidence_bundle or [])
            if e.get("evidence_id") not in selected_ids
        ],
    }
    return selected, audit

def compact_packet_for_budget(packet: dict[str, Any], profile: ModelBudgetProfile):
    out = dict(packet or {})
    out["missing_information"] = list(out.get("missing_information") or [])[:profile.max_missing_findings]
    out["contradictions"] = list(out.get("contradictions") or [])[:profile.max_contradictions]

    docs = []
    for d0 in list(out.get("structured_facts") or []):
        d = dict(d0)
        d["missing_fields"] = list(d.get("missing_fields") or [])[:profile.max_missing_findings]
        d["contradictions"] = list(d.get("contradictions") or [])[:profile.max_contradictions]
        docs.append(d)
    out["structured_facts"] = docs
    return out

def response_contract(profile: ModelBudgetProfile) -> str:
    return "\n".join([
        "",
        "=== CONTEXT BUDGET MANAGER RESPONSE CONTRACT ===",
        "Return exactly one compact JSON object with only conclusion, missing_information, and recommended_next_step.",
        "Prioritize valid JSON completion over explanatory detail.",
        "Conclusion: maximum 45 words.",
        "Do not generate applicable_authority, evidence, limitations, or safety; BioSafe assembles those deterministically.",
        f"Missing information: maximum {profile.max_missing_findings} concise items.",
        f"Recommended next steps: maximum {profile.max_recommendations} concise items.",
        f"Limitations: maximum {profile.max_limitations} concise items.",
        "Generate ONLY these keys: conclusion, missing_information, recommended_next_step.",
        "No prose before or after the JSON object.",
        "=== END CONTEXT BUDGET MANAGER RESPONSE CONTRACT ===",
    ])

def audit_prompt(model_id: str, messages: list[dict[str, Any]], evidence_audit: dict[str, Any]):
    profile = select_profile(model_id)
    prompt_text = "\n".join(str(m.get("content") or "") for m in messages)
    estimated = estimate_tokens(prompt_text)
    return {
        "profile": asdict(profile),
        "estimated_prompt_tokens": estimated,
        "within_target": estimated <= profile.target_prompt_tokens,
        "within_hard_budget": estimated <= profile.hard_prompt_tokens,
        "evidence": evidence_audit,
    }
