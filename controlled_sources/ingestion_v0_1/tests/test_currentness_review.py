from __future__ import annotations

import csv
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
from biosafe_controlled_ingestion.currentness_review import (  # noqa: E402
    build_currentness_evidence_packet,
)


REGISTER = ROOT / "controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv"
POLICY = INGESTION / "config/source_policy_v0_1.json"
AMENDMENT = ROOT / "controlled_sources/staging_v0_1/KB-MY-AMEND2019_reconciliation_v0_1.json"
SUPPORT = INGESTION / "human_review/MY-AUTH-EXACT-SUPPORT-01/exact_support_review_accepted.json"


class CurrentnessReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register_bytes = REGISTER.read_bytes()
        cls.policy_bytes = POLICY.read_bytes()
        cls.amendment_bytes = AMENDMENT.read_bytes()
        cls.support_bytes = SUPPORT.read_bytes()
        with REGISTER.open(encoding="utf-8", newline="") as stream:
            cls.register = list(csv.DictReader(stream, delimiter="\t"))
        cls.policy = json.loads(cls.policy_bytes)
        cls.amendment = json.loads(cls.amendment_bytes)
        cls.support = json.loads(cls.support_bytes)

    def build(self, register=None, amendment=None, support=None):
        return build_currentness_evidence_packet(
            register or self.register, self.register_bytes,
            self.policy, self.policy_bytes,
            amendment or self.amendment, self.amendment_bytes,
            support or self.support, self.support_bytes,
        )

    def test_packet_is_exact_scope_and_fail_closed(self):
        packet = self.build()
        self.assertEqual(
            {item["provision_id"] for item in packet["provisions"]},
            {"ACT678-S22-1-A-C", "REG2010-REG16-1-2", "REG2010-REG2B-FIRST-SCHEDULE"},
        )
        self.assertTrue(all(item["currentness_outcome"] == "CURRENTNESS_UNRESOLVED" for item in packet["provisions"]))
        self.assertEqual(packet["human_review_status"], "HUMAN_REVIEW_REQUIRED")
        self.assertEqual(packet["promotion_status"], "NOT_PROMOTED")
        self.assertEqual(packet["live_activation_status"], "PROHIBITED_PENDING_PHASE_C_GATES")

    def test_regulations_schedule_coverage_is_complete(self):
        packet = self.build()
        item = next(item for item in packet["provisions"] if item["provision_id"] == "REG2010-REG2B-FIRST-SCHEDULE")
        self.assertEqual(item["source_pages"], [21, 30, 31, 32, 33, 34])

    def test_missing_amendment_fails_closed(self):
        changed = json.loads(json.dumps(self.amendment))
        changed["amendment_document_id"] = "OTHER"
        with self.assertRaisesRegex(ValidationError, "amendment identity is invalid"):
            self.build(amendment=changed)

    def test_register_hash_drift_fails_closed(self):
        changed = json.loads(json.dumps(self.register))
        next(row for row in changed if row["candidate_id"] == "KB-MY-REG2010")["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "source hash mismatch"):
            self.build(register=changed)

    def test_amendment_is_not_treated_as_regulations_amendment(self):
        packet = self.build()
        self.assertEqual(packet["amendment_scope"]["target_instrument"], "Biosafety Act 2007 [Act 678]")
        self.assertEqual(
            packet["amendment_scope"]["non_target_instrument"],
            "Biosafety (Approval and Notification) Regulations 2010 [P.U. (A) 367/2010]",
        )


if __name__ == "__main__":
    unittest.main()