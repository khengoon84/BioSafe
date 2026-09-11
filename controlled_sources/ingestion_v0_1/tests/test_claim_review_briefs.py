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

from biosafe_controlled_ingestion.claim_review_briefs import (  # noqa: E402
    BRIEF_VERSION,
    build_claim_review_briefs,
    write_claim_review_briefs,
)
from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402


AID = INGESTION / "reports/claim_reconciliation_review_aid_v0_1.json"
REVIEW_MAP = INGESTION / "config/claim_reconciliation_map_v0_1.json"


class ClaimReviewBriefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aid_bytes = AID.read_bytes()
        cls.map_bytes = REVIEW_MAP.read_bytes()
        cls.aid = json.loads(cls.aid_bytes)

    def build(self, aid=None, map_bytes=None):
        return build_claim_review_briefs(
            aid or self.aid,
            self.aid_bytes,
            map_bytes or self.map_bytes,
            "controlled_sources/ingestion_v0_1/reports/claim_reconciliation_review_aid_v0_1.json",
            "controlled_sources/ingestion_v0_1/config/claim_reconciliation_map_v0_1.json",
            "2026-09-10",
        )

    def test_exact_pending_set_is_grouped_into_document_briefs(self):
        briefs, index = self.build()
        pending = {
            item["claim_id"]
            for item in self.aid["claim_review_items"]
            if item["claim_review_status"] == "REVIEW_REQUIRED_BEFORE_CLAIM_USE"
        }
        rendered = {
            line.removeprefix("## ")
            for content in briefs.values()
            for line in content.splitlines()
            if line.startswith("## CLM-")
        }
        self.assertEqual(len(briefs), 0)
        self.assertEqual(len(pending), 0)
        self.assertEqual(rendered, pending)
        self.assertIn("**0 pending claims across 0 controlled documents.**", index)

    def test_output_is_navigation_only_and_exposes_exact_contract(self):
        briefs, index = self.build()
        combined = index + "\n" + "\n".join(briefs.values())
        self.assertIn(BRIEF_VERSION, combined)
        self.assertIn("navigation-only aids", combined)
        self.assertIn("0 pending claims", combined)
        self.assertNotIn("Recommended disposition", combined)

    def test_build_is_deterministic_and_writer_emits_exact_file_set(self):
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_claim_review_briefs(*first, output)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {"INDEX.md"} | {f"review_brief_{doc}.md" for doc in first[0]},
            )

    def test_review_map_hash_drift_fails_closed(self):
        with self.assertRaisesRegex(ValidationError, "not bound"):
            self.build(map_bytes=self.map_bytes + b"\n")

    def test_tampered_pending_count_fails_closed(self):
        changed = json.loads(json.dumps(self.aid))
        changed["pending_claim_review_count"] += 1
        with self.assertRaisesRegex(ValidationError, "count does not match"):
            self.build(aid=changed)

    def test_public_cli_writes_exact_expected_briefs(self):
        expected_briefs, expected_index = build_claim_review_briefs(
            self.aid, self.aid_bytes, self.map_bytes,
            str(AID), str(REVIEW_MAP), "2026-09-10",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(SRC)
            result = subprocess.run(
                [
                    sys.executable,
                    str(INGESTION / "scripts/generate_claim_review_briefs.py"),
                    "--review-aid", str(AID),
                    "--review-map", str(REVIEW_MAP),
                    "--output-dir", str(output),
                    "--generated-date", "2026-09-10",
                ],
                capture_output=True, text=True, env=environment, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((output / "INDEX.md").read_text(), expected_index)
            for document_id, expected in expected_briefs.items():
                self.assertEqual(
                    (output / f"review_brief_{document_id}.md").read_text(), expected
                )
            self.assertIn("briefs=0 pending_claims=0", result.stdout)


if __name__ == "__main__":
    unittest.main()