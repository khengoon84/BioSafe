from __future__ import annotations

import csv
import io
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
from biosafe_controlled_ingestion.legal_blocker_evidence import (  # noqa: E402
    TARGET_CLAIMS,
    build_legal_blocker_evidence,
)


PATHS = {
    "draft": INGESTION / "reports/legal_claim_review_draft_v0_1.json",
    "map": INGESTION / "config/claim_reconciliation_map_v0_1.json",
    "components": INGESTION / "reports/component_candidates_v0_1.json",
    "policy": INGESTION / "config/source_policy_v0_1.json",
    "register": ROOT / "controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv",
}


class LegalBlockerEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {name: path.read_bytes() for name, path in PATHS.items()}
        cls.data = {
            name: json.loads(value)
            for name, value in cls.raw.items()
            if name != "register"
        }
        cls.data["register"] = list(csv.DictReader(
            io.StringIO(cls.raw["register"].decode("utf-8")), delimiter="\t"
        ))

    def build(self, **changes):
        data = dict(self.data)
        data.update(changes)
        return build_legal_blocker_evidence(
            data["draft"], self.raw["draft"],
            data["map"], self.raw["map"],
            data["components"], self.raw["components"],
            data["policy"], self.raw["policy"],
            data["register"], self.raw["register"], "2026-09-10",
        )

    def test_exact_three_claims_and_safety_boundary(self):
        bundles, index = self.build()
        self.assertEqual(set(bundles), TARGET_CLAIMS)
        self.assertIn("visually transcribed as an Act 678 amendment", index)
        for claim_id, content in bundles.items():
            self.assertIn(f"# Legal blocker evidence — {claim_id}", content)
            self.assertIn("Current disposition in canonical map: `CURRENTNESS_UNRESOLVED`", content)
            self.assertIn("does not establish current law", content)
            self.assertIn("does not change the claim disposition", content)

    def test_expected_source_passages_are_included(self):
        bundles, _ = self.build()
        self.assertIn("17.       (1)", bundles["CLM-006"])
        self.assertIn("19.", bundles["CLM-006"])
        self.assertIn("Host-Vector System", bundles["CLM-007"])
        self.assertIn("exemption list for Notification", bundles["CLM-007"])
        self.assertIn(
            "KB-MY-SW2005:AMENDMENT_LIST:PDF_PAGE_34", bundles["CLM-030"]
        )
        self.assertIn("SENARAI         PINDAAN", bundles["CLM-030"])
        self.assertIn("P.U. (A) 158    /2007", bundles["CLM-030"])
        self.assertIn(
            "`AMENDMENT_RECONCILIATION_AND_SYMBOLSET_VISUAL_VERIFICATION_REQUIRED`",
            bundles["CLM-030"],
        )
        self.assertIn("Peraturan      8.", bundles["CLM-030"])

    def test_build_is_deterministic(self):
        self.assertEqual(self.build(), self.build())

    def test_component_provenance_drift_fails_closed(self):
        changed = json.loads(json.dumps(self.data["draft"]))
        changed["source_component_artifact_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "not bound"):
            self.build(draft=changed)

    def test_canonical_disposition_drift_fails_closed(self):
        changed = json.loads(json.dumps(self.data["map"]))
        review = next(item for item in changed["claim_reviews"] if item["claim_id"] == "CLM-007")
        review["disposition"] = "SUPPORTED_EXACTLY"
        with self.assertRaisesRegex(ValidationError, "canonical blocker disposition"):
            self.build(map=changed)

    def test_unexpected_2019_amendment_register_record_fails_closed(self):
        changed = json.loads(json.dumps(self.data["register"]))
        record = dict(changed[0])
        record["candidate_id"] = "KB-MY-REG2019-AMENDMENT"
        record["title"] = "2019 First and Third Schedule amendment"
        changed.append(record)
        with self.assertRaisesRegex(ValidationError, "unexpected 2019 amendment record"):
            self.build(register=changed)


if __name__ == "__main__":
    unittest.main()