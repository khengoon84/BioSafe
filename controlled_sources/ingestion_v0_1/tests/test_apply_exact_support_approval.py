from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INGESTION = ROOT / "controlled_sources/ingestion_v0_1"
SRC = INGESTION / "src"
SCRIPTS = INGESTION / "scripts"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(SCRIPTS))

from apply_exact_support_approval import apply_approval  # noqa: E402
from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402


MAP = INGESTION / "config/claim_reconciliation_map_v0_1.json"
SUPPORT = INGESTION / "human_review/MY-AUTH-EXACT-SUPPORT-01/exact_support_review_accepted.json"


class ApplyExactSupportApprovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_bytes = MAP.read_bytes()
        cls.support_bytes = SUPPORT.read_bytes()
        cls.review_map = json.loads(cls.map_bytes)
        cls.support = json.loads(cls.support_bytes)

    def test_approval_populates_support_but_keeps_fail_closed_status(self):
        result = apply_approval(self.review_map, self.map_bytes, self.support, self.support_bytes)
        reviews = {item["claim_id"]: item for item in result["claim_reviews"]}
        for claim_id in ("CLM-005", "CLM-007"):
            review = reviews[claim_id]
            self.assertEqual(review["source_support_disposition"], "SUPPORTED_AFTER_ATOMIC_SPLIT")
            self.assertEqual(review["disposition"], "CURRENTNESS_UNRESOLVED")
            self.assertEqual(review["currentness_status"], "CURRENTNESS_UNRESOLVED")
            self.assertEqual(review["promotion_status"], "NOT_PROMOTED")
            self.assertEqual(review["allowed_actions"], [])
            self.assertEqual(review["allowed_decision_types"], [])
            self.assertTrue(review["support_spans"])

    def test_clm005_has_typed_context_dependency(self):
        result = apply_approval(self.review_map, self.map_bytes, self.support, self.support_bytes)
        review = next(item for item in result["claim_reviews"] if item["claim_id"] == "CLM-005")
        self.assertEqual(review["support_spans"][0]["atomic_proposition_indexes"], [1])
        self.assertEqual(review["dependency_support_spans"][0]["support_type"], "CONTEXT")
        self.assertEqual(review["cross_document_dependencies"][0]["source_document_id"], "KB-MY-ACT678")
        self.assertFalse(review["cross_document_dependencies"][0]["direct_canonical_support"])

    def test_rejects_non_accepted_or_promoted_packet(self):
        changed = json.loads(json.dumps(self.support))
        changed["promotion_status"] = "PROMOTED"
        with self.assertRaisesRegex(ValidationError, "must not be promoted"):
            apply_approval(self.review_map, self.map_bytes, changed, self.support_bytes)


if __name__ == "__main__":
    unittest.main()