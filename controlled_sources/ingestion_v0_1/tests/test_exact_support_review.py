from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
INGESTION = ROOT / "controlled_sources/ingestion_v0_1"
SRC = INGESTION / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402
from biosafe_controlled_ingestion.exact_support_review import (  # noqa: E402
    accept_source_support_review,
    build_exact_support_review_packet,
)


COMPONENT = INGESTION / "reports/component_candidates_v0_1.json"
AMENDMENT = ROOT / "controlled_sources/staging_v0_1/KB-MY-AMEND2019_reconciliation_v0_1.json"


class ExactSupportReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.component_bytes = COMPONENT.read_bytes()
        cls.amendment_bytes = AMENDMENT.read_bytes()
        cls.component = json.loads(cls.component_bytes)
        cls.amendment = json.loads(cls.amendment_bytes)

    def build(self, component=None, amendment=None):
        return build_exact_support_review_packet(
            component or self.component, self.component_bytes,
            amendment_artifact=amendment or self.amendment,
            amendment_artifact_bytes=self.amendment_bytes,
        )

    def test_exact_claims_pages_support_and_safety_boundary(self):
        packet = self.build()
        self.assertEqual(packet["claim_ids"], ["CLM-005", "CLM-007"])
        self.assertEqual(packet["human_review_status"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(packet["promotion_status"], "NOT_PROMOTED")
        self.assertEqual(packet["entries"][0]["required_pdf_pages"], [27, 83, 84])
        self.assertEqual(packet["entries"][1]["required_pdf_pages"], [21, 30, 31, 32, 33, 34])
        self.assertTrue(all(not item["support_spans"] == [] for item in packet["entries"]))
        self.assertTrue(all(item["currentness"] == "UNRESOLVED" for item in packet["entries"]))

    def test_quotes_are_exact_and_sources_are_not_amendment(self):
        packet = self.build()
        for entry in packet["entries"]:
            self.assertTrue(all(span["source_kind"] == "NATIVE_CANDIDATE" for span in entry["support_spans"]))
            self.assertNotIn("KB-MY-AMEND2019", " ".join(span["source_record_id"] for span in entry["support_spans"]))
            self.assertEqual(
                {index for span in entry["support_spans"] for index in span["atomic_proposition_indexes"]},
                set(range(1, len(entry["atomic_propositions"]) + 1)),
            )

    def test_missing_schedule_page_fails_closed(self):
        changed = json.loads(json.dumps(self.component))
        changed["candidate_chunks"] = [
            item for item in changed["candidate_chunks"]
            if item["candidate_chunk_id"] != "KB-MY-REG2010:PUA367:PDF_PAGE_33"
        ]
        with self.assertRaisesRegex(ValidationError, "required candidate is missing"):
            self.build(component=changed)

    def test_quote_drift_fails_closed(self):
        changed = json.loads(json.dumps(self.component))
        item = next(item for item in changed["candidate_chunks"] if item["candidate_chunk_id"].endswith("PDF_PAGE_83"))
        item["text"] = item["text"].replace("No   person", "Altered person")
        with self.assertRaisesRegex(ValidationError, "exact substring"):
            self.build(component=changed)

    def test_amendment_artifact_cannot_be_used_as_claim_support(self):
        changed = json.loads(json.dumps(self.amendment))
        changed["claim_use_status"] = "APPROVED"
        with self.assertRaisesRegex(ValidationError, "amendment artifact must require claim review"):
            self.build(amendment=changed)

    def test_acceptance_completes_source_review_but_not_currentness_or_promotion(self):
        accepted = accept_source_support_review(
            self.build(),
            reviewer_identity="BioSafe project owner",
            reviewer_role="Claim reconciliation reviewer",
            review_date="2026-09-13",
        )
        self.assertEqual(accepted["human_review_status"], "HUMAN_REVIEW_COMPLETE")
        self.assertEqual(accepted["promotion_status"], "NOT_PROMOTED")
        self.assertEqual(accepted["review_decision"]["decision"], "ACCEPT_EXACT_SUPPORT_PACKET_AS_REVIEWED")
        for entry in accepted["entries"]:
            self.assertEqual(entry["currentness"], "UNRESOLVED")
            self.assertEqual(entry["authority_status"], "AUTHORITATIVE_SOURCE_IDENTITY_VERIFIED_CURRENTNESS_UNRESOLVED")
            self.assertEqual(entry["jurisdiction"], "Malaysia")
            self.assertEqual(entry["allowed_actions"], [])
            self.assertEqual(entry["allowed_decision_types"], [])
            self.assertEqual(entry["review_status"], "HUMAN_REVIEW_COMPLETE")

    def test_acceptance_rejects_currentness_or_promotion_changes(self):
        changed = self.build()
        changed["promotion_status"] = "PROMOTED"
        with self.assertRaisesRegex(ValidationError, "promoted packet"):
            accept_source_support_review(changed, reviewer_identity="BioSafe project owner", reviewer_role="Reviewer", review_date="2026-09-13")


if __name__ == "__main__":
    unittest.main()