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

from biosafe_controlled_ingestion.components import (  # noqa: E402
    ACTIVATION_PROHIBITED,
    CLAIM_REVIEW_REQUIRED,
)
from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402
from biosafe_controlled_ingestion.legal_claim_review_draft import (  # noqa: E402
    DRAFT_SCOPE,
    LEGAL_CLAIM_IDS,
    build_legal_claim_review_draft,
    write_legal_claim_review_draft,
)


PATHS = {
    "draft_map": INGESTION / "config/legal_claim_review_draft_map_v0_1.json",
    "review_map": INGESTION / "reports/claim_reconciliation_map_v0_1_pre_legal_review.json",
    "source_policy": INGESTION / "config/source_policy_v0_1.json",
    "component_artifact": INGESTION / "reports/component_candidates_v0_1.json",
}


class LegalClaimReviewDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {name: path.read_bytes() for name, path in PATHS.items()}
        cls.data = {name: json.loads(value) for name, value in cls.raw.items()}
        cls.artifact = cls.build()

    @classmethod
    def build(cls, **changes):
        data = dict(cls.data)
        data.update(changes)
        return build_legal_claim_review_draft(
            data["draft_map"], cls.raw["draft_map"],
            data["review_map"], cls.raw["review_map"],
            data["source_policy"], cls.raw["source_policy"],
            data["component_artifact"], cls.raw["component_artifact"],
        )

    def test_artifact_covers_exact_nine_claims_and_cannot_make_decisions(self):
        self.assertEqual(self.artifact["artifact_scope"], DRAFT_SCOPE)
        self.assertEqual(self.artifact["legal_claim_count"], 9)
        self.assertEqual(
            {item["claim_id"] for item in self.artifact["legal_claim_drafts"]},
            LEGAL_CLAIM_IDS,
        )
        self.assertEqual(self.artifact["draft_dispositions_present"], 0)
        self.assertEqual(self.artifact["claim_use_status"], CLAIM_REVIEW_REQUIRED)
        self.assertEqual(self.artifact["live_activation_status"], ACTIVATION_PROHIBITED)
        for item in self.artifact["legal_claim_drafts"]:
            self.assertEqual(item["claim_review_status"], CLAIM_REVIEW_REQUIRED)
            self.assertIsNone(item["draft_disposition"])
            self.assertIsNone(item["automated_claim_update"])
            self.assertIsNone(item["reviewer_identity"])
            self.assertIsNone(item["reviewer_attestations"])

    def test_evidence_is_confined_to_controlled_document_and_hash(self):
        for item in self.artifact["legal_claim_drafts"]:
            for evidence in item["candidate_evidence"]:
                self.assertTrue(evidence["candidate_chunk_id"].startswith(item["controlled_document_id"] + ":"))
                self.assertEqual(evidence["source_sha256"], item["controlled_source_sha256"])

    def test_controlled_supersession_blocker_is_never_omitted(self):
        for item in self.artifact["legal_claim_drafts"]:
            self.assertIn(item["controlled_supersession_status"], item["currentness_blockers"])

    def test_material_legacy_claim_issues_are_explicit(self):
        by_id = {item["claim_id"]: item for item in self.artifact["legal_claim_drafts"]}
        self.assertTrue(any("MATERIAL_SECTION_CONTENT_MISMATCH" in issue for issue in by_id["CLM-006"]["review_issues"]))
        self.assertTrue(any("CURRENTNESS_BLOCKED" in issue for issue in by_id["CLM-007"]["review_issues"]))
        self.assertTrue(any("COMPOSITE_SOURCE_AND_PROJECT_POLICY" in issue for issue in by_id["CLM-030"]["review_issues"]))
        self.assertTrue(any("not automatically SW 404" in issue for issue in by_id["CLM-029"]["review_issues"]))

    def test_unknown_candidate_or_missing_locator_fails_closed(self):
        changed = json.loads(json.dumps(self.data["draft_map"]))
        changed["drafts"][0]["candidate_chunk_ids"] = ["UNKNOWN"]
        with self.assertRaisesRegex(ValidationError, "candidate does not exist"):
            self.build(draft_map=changed)
        changed = json.loads(json.dumps(self.data["draft_map"]))
        changed["drafts"][0]["locator_phrases"] = ["text absent from source"]
        with self.assertRaisesRegex(ValidationError, "locator phrase is absent"):
            self.build(draft_map=changed)

    def test_missing_claim_or_supersession_blocker_fails_closed(self):
        changed = json.loads(json.dumps(self.data["draft_map"]))
        changed["drafts"].pop()
        with self.assertRaisesRegex(ValidationError, "exact nine legal claims"):
            self.build(draft_map=changed)
        changed = json.loads(json.dumps(self.data["draft_map"]))
        changed["drafts"][0]["currentness_blockers"] = ["invented"]
        with self.assertRaisesRegex(ValidationError, "omits controlled supersession blocker"):
            self.build(draft_map=changed)

    def test_completed_claim_cannot_remain_in_draft(self):
        changed = json.loads(json.dumps(self.data["review_map"]))
        changed["claim_reviews"][0]["review_status"] = "CLAIM_REVIEW_COMPLETE"
        with self.assertRaisesRegex(ValidationError, "pending claim reviews"):
            self.build(review_map=changed)

    def test_serialization_and_public_cli_are_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "draft.json"
            write_legal_claim_review_draft(self.artifact, output)
            first = output.read_bytes()
            write_legal_claim_review_draft(self.artifact, output)
            self.assertEqual(first, output.read_bytes())
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(SRC)
            cli_output = Path(directory) / "cli.json"
            result = subprocess.run(
                [
                    sys.executable, str(INGESTION / "scripts/build_legal_claim_review_draft.py"),
                    "--draft-map", str(PATHS["draft_map"]),
                    "--review-map", str(PATHS["review_map"]),
                    "--source-policy", str(PATHS["source_policy"]),
                    "--component-artifact", str(PATHS["component_artifact"]),
                    "--output", str(cli_output),
                ],
                capture_output=True, text=True, env=environment, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first, cli_output.read_bytes())
            self.assertIn("legal_claims=9 draft_dispositions=0", result.stdout)


if __name__ == "__main__":
    unittest.main()