
from __future__ import annotations
from pathlib import Path
from structured_document_layer_v0_1 import BioSafeStructuredDocumentLayerV01
from normalized_document_profile_v0_1 import extract_normalized_profile, compare_profiles

TYPE_BY_PREFIX = {
    "SOP-01": "clinical_specimen_sop",
    "SOP-02": "biological_waste_sop",
    "SOP-03": "lmo_gmm_sop",
    "PROP-01": "lmo_gmm_proposal",
    "PROP-02": "clinical_specimen_proposal",
    "PROP-03": "other_biological_proposal",
    "FORM-E-SYNTHETIC-STRUCTURE": "form_e_structure",
    "FORM-E-SYNTHETIC-COMPLETED": "form_e_completed",
}

def document_type_for(filename: str) -> str:
    for prefix, doc_type in TYPE_BY_PREFIX.items():
        if filename.startswith(prefix):
            return doc_type
    return "unknown"

class BioSafeStructuredBenchmarkAdapterV01:
    def __init__(self, project_root: Path):
        data_dir = project_root / "data" / "structured_document_layer_v0_1"
        self.layer = BioSafeStructuredDocumentLayerV01(data_dir)

    def analyse(self, filename: str, text: str) -> dict:
        doc_type = document_type_for(filename)
        result = self.layer.analyse_document(filename, text, forced_type=doc_type)
        result["normalized_profile"] = extract_normalized_profile(text, doc_type)
        return result

    def build_packet(self, query: str, docs: list[dict], rag_evidence: list[dict], policy_mode: str) -> dict:
        packet = self.layer.build_packet(query, docs, rag_evidence, policy_mode)

        profile_conflicts = []
        if len(docs) >= 2:
            for i in range(len(docs)):
                for j in range(i + 1, len(docs)):
                    profile_conflicts.extend(compare_profiles(
                        docs[i]["document_id"], docs[i].get("normalized_profile", {}),
                        docs[j]["document_id"], docs[j].get("normalized_profile", {}),
                    ))

        # Prefer normalized-profile contradictions for cross-document tasks,
        # while preserving generic contradictions separately for audit.
        packet["generic_contradictions"] = packet.get("contradictions", [])
        packet["profile_contradictions"] = profile_conflicts
        packet["contradictions"] = profile_conflicts or packet["generic_contradictions"]
        packet["document_review_boundary"] = (
            "User documents describe the user's scenario and are not regulatory authority. "
            "Do not certify compliance. Do not invent absent facts. "
            "Treat missing information and contradictions as explicit findings."
        )
        return packet
