
from __future__ import annotations
import json
from pathlib import Path
from document_type_classifier_v0_1 import classify_document
from fact_extractor_v0_1 import extract_rule_based_facts, find_vague_statements
from missing_field_detector_v0_1 import detect_missing_fields
from contradiction_detector_v0_1 import compare_fact_sets

class BioSafeStructuredDocumentLayerV01:
    def __init__(self, data_dir: str | Path):
        data_dir = Path(data_dir)
        self.rules = json.loads((data_dir / "field_rules_v0.1.json").read_text(encoding="utf-8"))
        self.vague_terms = json.loads((data_dir / "vague_terms_v0.1.json").read_text(encoding="utf-8"))

    def analyse_document(self, document_id: str, text: str, forced_type: str | None = None) -> dict:
        cls = classify_document(text)
        doc_type = forced_type or cls["document_type"]
        rules = self.rules.get(doc_type, [])
        facts = extract_rule_based_facts(text, rules)
        missing = detect_missing_fields(facts, rules)
        vague = find_vague_statements(text, self.vague_terms)
        return {
            "document_id": document_id,
            "document_type": doc_type,
            "jurisdiction_hint": "Malaysia" if "malaysia" in text.lower() else "Unknown",
            "facts": facts,
            "missing_fields": missing,
            "contradictions": [],
            "extraction_notes": [f"Vague statement detected: {x}" for x in vague]
        }

    def compare_documents(self, doc_a: dict, doc_b: dict, comparable_fields: list[str] | None = None) -> list[dict]:
        return compare_fact_sets(doc_a, doc_b, comparable_fields=comparable_fields)

    def build_packet(self, query: str, docs: list[dict], rag_evidence: list[dict], policy_mode: str) -> dict:
        contradictions = []
        if len(docs) >= 2:
            for i in range(len(docs)):
                for j in range(i+1, len(docs)):
                    contradictions.extend(self.compare_documents(docs[i], docs[j]))
        missing = []
        for d in docs:
            for m in d.get("missing_fields", []):
                missing.append({"document_id": d["document_id"], **m})
        return {
            "query": query,
            "documents": [d["document_id"] for d in docs],
            "structured_facts": docs,
            "missing_information": missing,
            "contradictions": contradictions,
            "rag_evidence": rag_evidence,
            "policy_mode": policy_mode
        }
