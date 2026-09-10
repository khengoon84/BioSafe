from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INGESTION = ROOT / "controlled_sources/ingestion_v0_1"
SRC = INGESTION / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
SCRIPTS = INGESTION / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from apply_legal_currentness_unresolved_review import apply_review  # noqa: E402
from biosafe_controlled_ingestion.claim_reconciliation import (  # noqa: E402
    CLAIM_REVIEW_COMPLETE,
    build_claim_reconciliation_artifacts,
)
from biosafe_controlled_ingestion.components import (  # noqa: E402
    ACTIVATION_PROHIBITED,
    CLAIM_REVIEW_REQUIRED,
)
from biosafe_controlled_ingestion.legal_claim_review_draft import LEGAL_CLAIM_IDS  # noqa: E402


PATHS = {
    "crosswalk": INGESTION / "config/document_identity_crosswalk_v0_1.json",
    "review_map": INGESTION / "reports/claim_reconciliation_map_v0_1_pre_legal_review.json",
    "legal_draft": INGESTION / "reports/legal_claim_review_draft_v0_1.json",
    "knowledge_base": ROOT / "data/BioSafe_Knowledge_Base_v0.2.json",
    "component_artifact": INGESTION / "reports/component_candidates_v0_1.json",
    "fallback_artifact": INGESTION / "reports/semantic_fallbacks_v0_1.json",
    "fallback_review_packet": INGESTION / "reports/fallback_human_review_packet_v0_1.json",
}


class ApplyLegalCurrentnessReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {name: path.read_bytes() for name, path in PATHS.items()}
        cls.data = {name: json.loads(value) for name, value in cls.raw.items()}

    def apply(self):
        return apply_review(
            self.data["review_map"], self.data["legal_draft"],
            reviewer_identity="BioSafe project owner",
            reviewer_role="Claim reconciliation reviewer",
            review_date="2026-09-10",
        )

    def test_exact_nine_are_completed_currentness_unresolved_and_none_supported(self):
        result = self.apply()
        completed = [item for item in result["claim_reviews"] if item["review_status"] == CLAIM_REVIEW_COMPLETE]
        self.assertEqual({item["claim_id"] for item in completed}, LEGAL_CLAIM_IDS)
        self.assertTrue(all(item["disposition"] == "CURRENTNESS_UNRESOLVED" for item in completed))
        self.assertTrue(all(item["support_spans"] == [] for item in completed))
        self.assertEqual(
            sum(item["review_status"] == CLAIM_REVIEW_REQUIRED for item in result["claim_reviews"]),
            36,
        )

    def test_review_evidence_and_boundaries_are_complete(self):
        result = self.apply()
        for item in result["claim_reviews"]:
            if item["claim_id"] not in LEGAL_CLAIM_IDS:
                continue
            self.assertEqual(item["reviewer_identity"], "BioSafe project owner")
            self.assertEqual(item["reviewer_role"], "Claim reconciliation reviewer")
            self.assertEqual(item["review_date"], "2026-09-10")
            self.assertEqual(set(item["check_results"].values()), {"PASS"})
            self.assertTrue(all(item["attestations"].values()))
            self.assertTrue(any("Do not curate" in value for value in item["exclusions"]))
            self.assertTrue(item["limitations"])
            self.assertTrue(item["findings"])

    def test_reconciliation_builder_accepts_reviews_but_curates_none(self):
        result = self.apply()
        packet, curated = build_claim_reconciliation_artifacts(
            self.data["crosswalk"], self.raw["crosswalk"], result,
            self.data["knowledge_base"], self.raw["knowledge_base"],
            self.data["component_artifact"], self.raw["component_artifact"],
            self.data["fallback_artifact"], self.raw["fallback_artifact"],
            self.data["fallback_review_packet"], self.raw["fallback_review_packet"],
        )
        self.assertEqual(packet["completed_review_count"], 9)
        self.assertEqual(packet["required_review_count"], 45)
        self.assertEqual(packet["curated_claim_count"], 0)
        self.assertEqual(curated["curated_claims"], [])
        self.assertEqual(curated["claim_use_status"], CLAIM_REVIEW_REQUIRED)
        self.assertEqual(curated["live_activation_status"], ACTIVATION_PROHIBITED)

    def test_review_application_is_deterministic_and_refuses_reapplication(self):
        first = self.apply()
        second = self.apply()
        self.assertEqual(first, second)
        with self.assertRaisesRegex(ValueError, "not pending"):
            apply_review(
                first, self.data["legal_draft"],
                reviewer_identity="BioSafe project owner",
                reviewer_role="Claim reconciliation reviewer",
                review_date="2026-09-10",
            )

    def test_public_cli_writes_exact_expected_map(self):
        expected = self.apply()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "map.json"
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(SRC)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "apply_legal_currentness_unresolved_review.py"),
                    "--review-map", str(PATHS["review_map"]),
                    "--legal-draft", str(PATHS["legal_draft"]),
                    "--reviewer-identity", "BioSafe project owner",
                    "--reviewer-role", "Claim reconciliation reviewer",
                    "--review-date", "2026-09-10",
                    "--output", str(output),
                ],
                capture_output=True, text=True, env=environment, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_bytes()), expected)
            self.assertIn("completed_claim_reviews=9", result.stdout)


if __name__ == "__main__":
    unittest.main()