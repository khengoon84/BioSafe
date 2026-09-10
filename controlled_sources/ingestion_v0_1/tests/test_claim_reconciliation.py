from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INGESTION = ROOT / "controlled_sources/ingestion_v0_1"
SRC = INGESTION / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from biosafe_controlled_ingestion.claim_reconciliation import (  # noqa: E402
    CLAIM_REVIEW_COMPLETE,
    HUMAN_IDENTITY_REVIEW_COMPLETE,
    build_claim_reconciliation_artifacts,
    initialize_claim_reconciliation_map,
    validate_identity_crosswalk,
    write_json_atomic,
)
from biosafe_controlled_ingestion.components import (  # noqa: E402
    ACTIVATION_PROHIBITED,
    CLAIM_REVIEW_REQUIRED,
)
from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402
from biosafe_controlled_ingestion.legal_claim_review_draft import LEGAL_CLAIM_IDS  # noqa: E402


CROSSWALK = INGESTION / "config/document_identity_crosswalk_v0_1.json"
REVIEW_MAP = INGESTION / "config/claim_reconciliation_map_v0_1.json"
PRE_LEGAL_REVIEW_MAP = INGESTION / "reports/claim_reconciliation_map_v0_1_pre_legal_review.json"
KB = ROOT / "data/BioSafe_Knowledge_Base_v0.2.json"
COMPONENTS = INGESTION / "reports/component_candidates_v0_1.json"
FALLBACKS = INGESTION / "reports/semantic_fallbacks_v0_1.json"
FALLBACK_REVIEWS = INGESTION / "reports/fallback_human_review_packet_v0_1.json"


class ClaimReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.crosswalk_bytes = CROSSWALK.read_bytes()
        cls.kb_bytes = KB.read_bytes()
        cls.component_bytes = COMPONENTS.read_bytes()
        cls.fallback_bytes = FALLBACKS.read_bytes()
        cls.fallback_review_bytes = FALLBACK_REVIEWS.read_bytes()
        cls.crosswalk = json.loads(cls.crosswalk_bytes)
        cls.kb = json.loads(cls.kb_bytes)
        cls.components = json.loads(cls.component_bytes)
        cls.fallbacks = json.loads(cls.fallback_bytes)
        cls.fallback_reviews = json.loads(cls.fallback_review_bytes)
        cls.review_map = json.loads(REVIEW_MAP.read_text(encoding="utf-8"))
        cls.pre_legal_review_map = json.loads(PRE_LEGAL_REVIEW_MAP.read_text(encoding="utf-8"))

    def build(self, review_map=None, crosswalk=None, crosswalk_bytes=None):
        return build_claim_reconciliation_artifacts(
            crosswalk or self.crosswalk,
            crosswalk_bytes or self.crosswalk_bytes,
            review_map or self.review_map,
            self.kb,
            self.kb_bytes,
            self.components,
            self.component_bytes,
            self.fallbacks,
            self.fallback_bytes,
            self.fallback_reviews,
            self.fallback_review_bytes,
        )

    def test_initializer_reproduces_preserved_pending_baseline_and_canonical_delta_is_exact(self):
        result = initialize_claim_reconciliation_map(
            self.crosswalk,
            self.crosswalk_bytes,
            self.kb,
            self.kb_bytes,
            self.components,
            self.component_bytes,
            self.fallback_bytes,
            self.fallback_review_bytes,
        )
        self.assertEqual(result, self.pre_legal_review_map)
        self.assertEqual(len(result["claim_reviews"]), 45)
        self.assertTrue(all(item["review_status"] == CLAIM_REVIEW_REQUIRED for item in result["claim_reviews"]))
        pending_by_id = {item["claim_id"]: item for item in result["claim_reviews"]}
        canonical_by_id = {item["claim_id"]: item for item in self.review_map["claim_reviews"]}
        changed_ids = {
            claim_id for claim_id, item in pending_by_id.items()
            if canonical_by_id[claim_id] != item
        }
        self.assertEqual(changed_ids, set(LEGAL_CLAIM_IDS))
        for claim_id in LEGAL_CLAIM_IDS:
            completed = canonical_by_id[claim_id]
            self.assertEqual(completed["review_status"], CLAIM_REVIEW_COMPLETE)
            self.assertEqual(completed["disposition"], "CURRENTNESS_UNRESOLVED")
            self.assertEqual(completed["support_spans"], [])
        for claim_id, item in canonical_by_id.items():
            if claim_id not in LEGAL_CLAIM_IDS:
                self.assertEqual(item, pending_by_id[claim_id])

    def test_post_decision_packet_stays_additive_without_curated_claims(self):
        packet, curated = self.build()
        self.assertEqual(packet["required_review_count"], 45)
        self.assertEqual(packet["completed_review_count"], len(LEGAL_CLAIM_IDS))
        self.assertEqual(packet["curated_claim_count"], 0)
        self.assertEqual(packet["claim_use_status"], CLAIM_REVIEW_REQUIRED)
        self.assertEqual(packet["live_activation_status"], ACTIVATION_PROHIBITED)
        self.assertEqual(curated["curated_claims"], [])
        self.assertEqual(curated["artifact_scope"], "ADDITIVE_OFFLINE_CURATED_CANDIDATE_REFERENCE_ONLY")
        self.assertEqual(curated["live_activation_status"], ACTIVATION_PROHIBITED)

    def test_crosswalk_covers_exact_claim_documents_and_records_four_completed_aliases(self):
        mappings = validate_identity_crosswalk(self.crosswalk, self.kb, self.components)
        self.assertEqual(set(mappings), {claim["document_id"] for claim in self.kb["claims"]})
        completed = {
            legacy: item["controlled_document_id"]
            for legacy, item in mappings.items()
            if item["identity_review_status"] == HUMAN_IDENTITY_REVIEW_COMPLETE
        }
        self.assertEqual(completed, {
            "KB-MY-DOE2005": "KB-MY-SW2005",
            "KB-MY-MOH2023": "KB-MY-TRANSPORT2023",
            "KB-WHO-PPE": "KB-WHO-LBM4-PPE",
            "KB-WHO-RA": "KB-WHO-LBM4-RA",
        })

    def test_crosswalk_rejects_hash_mismatch_and_silent_alias_acceptance(self):
        bad_hash = json.loads(json.dumps(self.crosswalk))
        bad_hash["document_mappings"][0]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "source hash mismatch"):
            validate_identity_crosswalk(bad_hash, self.kb, self.components)
        silent = json.loads(json.dumps(self.crosswalk))
        alias = next(item for item in silent["document_mappings"] if item["legacy_document_id"] == "KB-MY-DOE2005")
        alias["identity_review_record"] = {
            "reviewer_identity": None, "reviewer_role": None, "review_date": None, "findings": []
        }
        with self.assertRaisesRegex(ValidationError, "identity review reviewer_identity"):
            validate_identity_crosswalk(silent, self.kb, self.components)

    def test_provenance_changes_fail_closed(self):
        changed = json.loads(json.dumps(self.review_map))
        changed["source_component_artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "provenance mismatch"):
            self.build(changed)
        changed_fallback_review = json.loads(json.dumps(self.fallback_reviews))
        changed_fallback_review["source_fallback_artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "not bound"):
            build_claim_reconciliation_artifacts(
                self.crosswalk, self.crosswalk_bytes, self.review_map, self.kb, self.kb_bytes,
                self.components, self.component_bytes, self.fallbacks, self.fallback_bytes,
                changed_fallback_review, self.fallback_review_bytes,
            )

    def test_fallback_support_requires_exact_accepted_unit_set(self):
        changed_packet = json.loads(json.dumps(self.fallback_reviews))
        changed_packet["review_items"][0]["review_record"]["disposition"] = "CORRECTION_REQUIRED"
        changed_bytes = (json.dumps(changed_packet, sort_keys=True) + "\n").encode("utf-8")
        changed_map = json.loads(json.dumps(self.review_map))
        changed_map["source_fallback_review_packet_sha256"] = hashlib.sha256(changed_bytes).hexdigest()
        with self.assertRaisesRegex(ValidationError, "exact fallback unit set"):
            build_claim_reconciliation_artifacts(
                self.crosswalk, self.crosswalk_bytes, changed_map, self.kb, self.kb_bytes,
                self.components, self.component_bytes, self.fallbacks, self.fallback_bytes,
                changed_packet, changed_bytes,
            )

    def _complete_first_direct_claim(self):
        changed = json.loads(json.dumps(self.review_map))
        review = next(
            item for item in changed["claim_reviews"]
            if item["review_status"] == CLAIM_REVIEW_REQUIRED
        )
        candidate = next(
            item for item in self.components["candidate_chunks"]
            if item["document_id"] == review["controlled_document_id"] and item["text"].strip()
        )
        quote = candidate["text"].splitlines()[0]
        review.update({
            "review_status": CLAIM_REVIEW_COMPLETE,
            "disposition": "SUPPORTED_EXACTLY",
            "atomic_propositions": ["Synthetic contract-test proposition."],
            "support_spans": [{
                "source_kind": "NATIVE_CANDIDATE",
                "source_record_id": candidate["candidate_chunk_id"],
                "support_type": "DIRECT",
                "atomic_proposition_indexes": [1],
                "pdf_page_start": candidate["pdf_page_start"],
                "pdf_page_end": candidate["pdf_page_end"],
                "quoted_support": quote,
            }],
            "authority_tier": "Tier 1",
            "jurisdiction": "Malaysia",
            "evidence_role": "MALAYSIAN_PRIMARY_LEGISLATION",
            "currentness_status": "CURRENTNESS_REVIEWED_FOR_CONTRACT_TEST",
            "supersession_status": "SUPERSESSION_REVIEWED_FOR_CONTRACT_TEST",
            "allowed_decision_types": [],
            "allowed_actions": [],
            "limitations": ["Synthetic record used only for deterministic contract testing."],
            "exclusions": ["Not a legal determination or live activation."],
            "reviewer_identity": "Synthetic contract-test reviewer",
            "reviewer_role": "Claim reconciliation test fixture",
            "review_date": "2026-09-10",
            "findings": ["Exact source substring used to exercise the contract."],
        })
        review["check_results"] = {key: "PASS" for key in review["check_results"]}
        review["attestations"] = {key: True for key in review["attestations"]}
        return changed, review

    def test_completed_exact_native_support_can_enter_offline_curated_candidate(self):
        changed, review = self._complete_first_direct_claim()
        packet, curated = self.build(changed)
        self.assertEqual(packet["completed_review_count"], len(LEGAL_CLAIM_IDS) + 1)
        self.assertEqual(curated["curated_claim_count"], 1)
        self.assertEqual(curated["curated_claims"][0]["claim_id"], review["claim_id"])
        self.assertEqual(curated["claim_use_status"], CLAIM_REVIEW_REQUIRED)
        self.assertEqual(curated["live_activation_status"], ACTIVATION_PROHIBITED)

    def test_completed_review_rejects_inexact_quote_or_page(self):
        changed, review = self._complete_first_direct_claim()
        review["support_spans"][0]["quoted_support"] = "not present in the candidate"
        with self.assertRaisesRegex(ValidationError, "occur exactly"):
            self.build(changed)
        changed, review = self._complete_first_direct_claim()
        review["support_spans"][0]["pdf_page_start"] += 1
        review["support_spans"][0]["pdf_page_end"] += 1
        with self.assertRaisesRegex(ValidationError, "page range must match"):
            self.build(changed)

    def test_alias_claim_cannot_complete_while_identity_review_is_pending(self):
        changed_crosswalk = json.loads(json.dumps(self.crosswalk))
        alias = next(item for item in changed_crosswalk["document_mappings"] if item["legacy_document_id"] == "KB-MY-DOE2005")
        alias["identity_review_status"] = "HUMAN_IDENTITY_REVIEW_REQUIRED"
        alias["identity_review_record"] = {
            "reviewer_identity": None, "reviewer_role": None, "review_date": None, "findings": []
        }
        changed_crosswalk_bytes = (json.dumps(changed_crosswalk, sort_keys=True) + "\n").encode("utf-8")
        changed = initialize_claim_reconciliation_map(
            changed_crosswalk, changed_crosswalk_bytes, self.kb, self.kb_bytes,
            self.components, self.component_bytes, self.fallback_bytes, self.fallback_review_bytes,
        )
        review = next(item for item in changed["claim_reviews"] if item["claim_id"] == "CLM-029")
        review["review_status"] = CLAIM_REVIEW_COMPLETE
        with self.assertRaisesRegex(ValidationError, "identity review is pending"):
            self.build(changed, changed_crosswalk, changed_crosswalk_bytes)

    def test_insufficient_evidence_can_complete_without_inventing_a_support_span(self):
        changed, review = self._complete_first_direct_claim()
        review["disposition"] = "INSUFFICIENT_EVIDENCE"
        review["support_spans"] = []
        packet, curated = self.build(changed)
        self.assertEqual(packet["completed_review_count"], len(LEGAL_CLAIM_IDS) + 1)
        self.assertEqual(curated["curated_claims"], [])

    def test_supported_disposition_requires_exact_support(self):
        changed, review = self._complete_first_direct_claim()
        review["support_spans"] = []
        with self.assertRaisesRegex(ValidationError, "must include exact support spans"):
            self.build(changed)

    def test_every_atomic_proposition_requires_direct_exact_support(self):
        changed, review = self._complete_first_direct_claim()
        review["atomic_propositions"].append("A second unsupported proposition.")
        with self.assertRaisesRegex(ValidationError, "every atomic proposition"):
            self.build(changed)

    def test_support_rejects_invalid_atomic_proposition_index(self):
        changed, review = self._complete_first_direct_claim()
        review["support_spans"][0]["atomic_proposition_indexes"] = [2]
        with self.assertRaisesRegex(ValidationError, "indexes are invalid"):
            self.build(changed)

    def test_inputs_must_remain_review_gated_and_activation_prohibited(self):
        components = json.loads(json.dumps(self.components))
        components["live_activation_status"] = "ACTIVE"
        with self.assertRaisesRegex(ValidationError, "must prohibit live activation"):
            build_claim_reconciliation_artifacts(
                self.crosswalk, self.crosswalk_bytes, self.review_map, self.kb, self.kb_bytes,
                components, self.component_bytes, self.fallbacks, self.fallback_bytes,
                self.fallback_reviews, self.fallback_review_bytes,
            )

    def test_serialization_is_deterministic(self):
        packet, _ = self.build()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "packet.json"
            write_json_atomic(packet, output)
            first = output.read_bytes()
            write_json_atomic(packet, output)
            self.assertEqual(first, output.read_bytes())


if __name__ == "__main__":
    unittest.main()