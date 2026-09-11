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

    def test_unsorted_duplicate_or_nonpending_claims_fail_closed(self):
        with self.assertRaisesRegex(ValidationError, "sorted unique"):
            self.build(["CLM-019", "CLM-018"])
        with self.assertRaisesRegex(ValidationError, "not pending"):
            self.build(["CLM-001"])
        with self.assertRaisesRegex(ValidationError, "not pending"):
            self.build(["CLM-018"])

    def test_non_form_e_worksheet_uses_claim_specific_boundaries(self):
        _, worksheet = self.build(["CLM-012"])
        self.assertIn(
            "Confirmed every claim-specific boundary prompt above was preserved",
            worksheet,
        )
        self.assertIn(
            "Risk group, organism hazard, procedure-specific risk, and containment level remain distinct.",
            worksheet,
        )
        self.assertNotIn("Confirmed Form E is not described", worksheet)


if __name__ == "__main__":
    unittest.main()