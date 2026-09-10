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

from biosafe_controlled_ingestion.claim_decision_entry import (  # noqa: E402
    HUMAN_REVIEW_REQUIRED,
)
from biosafe_controlled_ingestion.claim_decision_template import (  # noqa: E402
    initialize_decision_template,
)
from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402


MAP = INGESTION / "config/claim_reconciliation_map_v0_1.json"
AID = INGESTION / "reports/claim_reconciliation_review_aid_v0_1.json"
CLAIM_IDS = ["CLM-018", "CLM-019", "CLM-024", "CLM-025"]


class ClaimDecisionTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.map_bytes = MAP.read_bytes()
        cls.aid_bytes = AID.read_bytes()
        cls.review_map = json.loads(cls.map_bytes)
        cls.aid = json.loads(cls.aid_bytes)

    def build(self, claim_ids=None, map_bytes=None):
        return initialize_decision_template(
            self.review_map, map_bytes or self.map_bytes,
            self.aid, self.aid_bytes,
            claim_ids or CLAIM_IDS, "FORME-PILOT-01",
        )

    def test_exact_pilot_claims_are_incomplete_and_decision_free(self):
        packet, worksheet = self.build()
        self.assertEqual(packet["claim_ids"], CLAIM_IDS)
        self.assertEqual(packet["human_review_status"], HUMAN_REVIEW_REQUIRED)
        for decision in packet["decisions"]:
            self.assertEqual(decision["review_status"], "REVIEW_REQUIRED_BEFORE_CLAIM_USE")
            self.assertIsNone(decision["disposition"])
            self.assertEqual(decision["atomic_propositions"], [])
            self.assertEqual(decision["support_spans"], [])
            self.assertTrue(all(value is None for value in decision["check_results"].values()))
            self.assertTrue(all(value is False for value in decision["attestations"].values()))
        self.assertIn("No decision has been made by this template", worksheet)

    def test_worksheet_contains_exact_boundaries_and_navigation_ids(self):
        _, worksheet = self.build()
        self.assertIn("Form E is not an approval, submission, permit, or regulatory determination", worksheet)
        self.assertIn("KB-MY-FORME:FORM_E_INSTRUCTIONS:PDF_PAGE_202", worksheet)
        self.assertIn("KB-MY-FORME:FORM_E_IBC_ASSESSMENT:PDF_PAGE_208", worksheet)
        self.assertNotIn("Recommended disposition", worksheet)

    def test_template_is_deterministic_and_hash_drift_fails_closed(self):
        self.assertEqual(self.build(), self.build())
        with self.assertRaisesRegex(ValidationError, "not bound"):
            self.build(map_bytes=self.map_bytes + b"\n")

    def test_unsorted_duplicate_or_nonpending_claims_fail_closed(self):
        with self.assertRaisesRegex(ValidationError, "sorted unique"):
            self.build(["CLM-019", "CLM-018"])
        with self.assertRaisesRegex(ValidationError, "not pending"):
            self.build(["CLM-001"])

    def test_public_cli_emits_exact_outputs(self):
        expected_packet, expected_worksheet = self.build()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = root / "packet.json"
            worksheet = root / "worksheet.md"
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(SRC)
            command = [
                sys.executable, str(INGESTION / "scripts/initialize_claim_decision_template.py"),
                "--review-map", str(MAP), "--review-aid", str(AID),
                "--batch-id", "FORME-PILOT-01",
                "--packet-output", str(packet), "--worksheet-output", str(worksheet),
            ]
            for claim_id in CLAIM_IDS:
                command.extend(["--claim-id", claim_id])
            process = subprocess.run(command, capture_output=True, text=True, env=environment)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(packet.read_bytes()), expected_packet)
            self.assertEqual(worksheet.read_text(), expected_worksheet)
            self.assertIn("claims=4 human_review_status=HUMAN_REVIEW_REQUIRED", process.stdout)


if __name__ == "__main__":
    unittest.main()