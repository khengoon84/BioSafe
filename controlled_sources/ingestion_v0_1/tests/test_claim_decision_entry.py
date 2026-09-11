from __future__ import annotations

import hashlib
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
    DECISION_PACKET_VERSION,
    HUMAN_REVIEW_COMPLETE,
    apply_claim_decisions,
    canonical_json_bytes,
)
from biosafe_controlled_ingestion.contracts import ValidationError  # noqa: E402


PATHS = {
    "map": INGESTION / "config/claim_reconciliation_map_v0_1.json",
    "crosswalk": INGESTION / "config/document_identity_crosswalk_v0_1.json",
    "kb": ROOT / "data/BioSafe_Knowledge_Base_v0.2.json",
    "components": INGESTION / "reports/component_candidates_v0_1.json",
    "fallbacks": INGESTION / "reports/semantic_fallbacks_v0_1.json",
    "fallback_reviews": INGESTION / "reports/fallback_human_review_packet_v0_1.json",
}
SYNTHETIC_PENDING_CLAIM_ID = "CLM-032"


class ClaimDecisionEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {name: path.read_bytes() for name, path in PATHS.items()}
        cls.data = {name: json.loads(value) for name, value in cls.raw.items()}
        review = next(
            item for item in cls.data["map"]["claim_reviews"]
            if item["claim_id"] == SYNTHETIC_PENDING_CLAIM_ID
        )
        candidate = next(
            item for item in cls.data["components"]["candidate_chunks"]
            if item["document_id"] == review["controlled_document_id"] and item["text"].strip()
        )
        cls.candidate = candidate

    def decision_packet(self):
        quote = self.candidate["text"].splitlines()[0]
        decision = {
            "claim_id": SYNTHETIC_PENDING_CLAIM_ID,
            "review_status": "CLAIM_REVIEW_COMPLETE",
            "disposition": "SUPPORTED_EXACTLY",
            "atomic_propositions": ["Synthetic decision-entry contract proposition."],
            "support_spans": [{
                "source_kind": "NATIVE_CANDIDATE",
                "source_record_id": self.candidate["candidate_chunk_id"],
                "support_type": "DIRECT",
                "atomic_proposition_indexes": [1],
                "pdf_page_start": self.candidate["pdf_page_start"],
                "pdf_page_end": self.candidate["pdf_page_end"],
                "quoted_support": quote,
            }],
            "authority_tier": "Tier 2",
            "jurisdiction": "Malaysia",
            "evidence_role": "MALAYSIAN_OFFICIAL_GUIDANCE_TEST_FIXTURE",
            "currentness_status": "CURRENTNESS_REVIEWED_FOR_CONTRACT_TEST",
            "supersession_status": "SUPERSESSION_REVIEWED_FOR_CONTRACT_TEST",
            "allowed_decision_types": [],
            "allowed_actions": [],
            "limitations": ["Synthetic fixture; not a human claim decision."],
            "exclusions": ["Not for live activation or regulatory determination."],
            "reviewer_identity": "Synthetic contract-test reviewer",
            "reviewer_role": "Claim decision-entry test fixture",
            "review_date": "2026-09-10",
            "findings": ["Exact source substring used to test decision application."],
            "check_results": {
                key: "PASS"
                for key in next(
                    item for item in self.data["map"]["claim_reviews"]
                    if item["claim_id"] == SYNTHETIC_PENDING_CLAIM_ID
                )["check_results"]
            },
            "attestations": {
                key: True
                for key in next(
                    item for item in self.data["map"]["claim_reviews"]
                    if item["claim_id"] == SYNTHETIC_PENDING_CLAIM_ID
                )["attestations"]
            },
        }
        return {
            "decision_packet_version": DECISION_PACKET_VERSION,
            "human_review_status": HUMAN_REVIEW_COMPLETE,
            "batch_id": "SYNTHETIC-TEST-BATCH",
            "source_review_map_sha256": hashlib.sha256(self.raw["map"]).hexdigest(),
            "claim_ids": [SYNTHETIC_PENDING_CLAIM_ID],
            "decisions": [decision],
        }

    def apply(self, decision_packet=None, review_map=None, map_bytes=None):
        decisions = decision_packet or self.decision_packet()
        decision_bytes = canonical_json_bytes(decisions)
        return apply_claim_decisions(
            review_map or self.data["map"], map_bytes or self.raw["map"],
            decisions, decision_bytes,
            self.data["crosswalk"], self.raw["crosswalk"],
            self.data["kb"], self.raw["kb"],
            self.data["components"], self.raw["components"],
            self.data["fallbacks"], self.raw["fallbacks"],
            self.data["fallback_reviews"], self.raw["fallback_reviews"],
            "2026-09-10",
        )

    def test_applies_exactly_one_pending_claim_and_reports_curation(self):
        result, report = self.apply()
        changed = next(
            item for item in result["claim_reviews"]
            if item["claim_id"] == SYNTHETIC_PENDING_CLAIM_ID
        )
        original = next(item for item in self.data["map"]["claim_reviews"] if item["claim_id"] == "CLM-009")
        unchanged = next(item for item in result["claim_reviews"] if item["claim_id"] == "CLM-009")
        self.assertEqual(changed["review_status"], "CLAIM_REVIEW_COMPLETE")
        self.assertEqual(unchanged, original)
        self.assertEqual(report["changed_claim_ids"], [SYNTHETIC_PENDING_CLAIM_ID])
        self.assertEqual(report["total_completed_review_count"], 31)
        self.assertEqual(report["total_pending_review_count"], 14)
        self.assertEqual(report["curated_claim_ids"], [
            "CLM-008", "CLM-009", "CLM-010", "CLM-011", "CLM-012", "CLM-013", "CLM-014",
            "CLM-015", "CLM-016", "CLM-017",
            "CLM-021", "CLM-022", "CLM-023", "CLM-024", "CLM-025",
            "CLM-026", "CLM-027", "CLM-028", "CLM-032",
        ])
        self.assertEqual(report["live_activation_status"], "PROHIBITED_PENDING_PHASE_C_GATES")

    def test_result_and_report_are_deterministic(self):
        self.assertEqual(self.apply(), self.apply())

    def test_invalid_application_date_fails_closed(self):
        decisions = self.decision_packet()
        with self.assertRaisesRegex(ValidationError, "ISO calendar date"):
            apply_claim_decisions(
                self.data["map"], self.raw["map"], decisions, canonical_json_bytes(decisions),
                self.data["crosswalk"], self.raw["crosswalk"],
                self.data["kb"], self.raw["kb"],
                self.data["components"], self.raw["components"],
                self.data["fallbacks"], self.raw["fallbacks"],
                self.data["fallback_reviews"], self.raw["fallback_reviews"], "not-a-date",
            )

    def test_hash_tampering_and_declared_set_mismatch_fail_closed(self):
        changed = self.decision_packet()
        changed["source_review_map_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValidationError, "not bound"):
            self.apply(changed)

    def test_incomplete_human_review_is_refused(self):
        changed = self.decision_packet()
        changed["human_review_status"] = "HUMAN_REVIEW_REQUIRED"
        with self.assertRaisesRegex(ValidationError, "completed human review"):
            self.apply(changed)

    def test_invalid_source_map_fails_before_decision_application(self):
        changed_map = json.loads(json.dumps(self.data["map"]))
        review = next(item for item in changed_map["claim_reviews"] if item["claim_id"] == "CLM-009")
        review["controlled_source_sha256"] = "0" * 64
        changed_bytes = canonical_json_bytes(changed_map)
        decisions = self.decision_packet()
        decisions["source_review_map_sha256"] = hashlib.sha256(changed_bytes).hexdigest()
        with self.assertRaisesRegex(ValidationError, "identity binding mismatch"):
            self.apply(decisions, review_map=changed_map, map_bytes=changed_bytes)
        changed = self.decision_packet()
        changed["claim_ids"] = ["CLM-009"]
        with self.assertRaisesRegex(ValidationError, "exactly match"):
            self.apply(changed)

    def test_inexact_quote_fails_existing_reconciliation_validator(self):
        changed = self.decision_packet()
        changed["decisions"][0]["support_spans"][0]["quoted_support"] = "not in source"
        with self.assertRaisesRegex(ValidationError, "occur exactly"):
            self.apply(changed)

    def test_reapplication_is_refused(self):
        first, _ = self.apply()
        changed = self.decision_packet()
        changed["source_review_map_sha256"] = hashlib.sha256(
            canonical_json_bytes(first)
        ).hexdigest()
        with self.assertRaisesRegex(ValidationError, "not pending"):
            self.apply(changed, review_map=first, map_bytes=canonical_json_bytes(first))

    def test_public_cli_writes_exact_snapshot_map_and_report(self):
        decisions = self.decision_packet()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decision_path = root / "decisions.json"
            decision_path.write_bytes(canonical_json_bytes(decisions))
            output = root / "map.json"
            snapshot = root / "snapshot.json"
            report = root / "report.json"
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(SRC)
            command = [
                sys.executable, str(INGESTION / "scripts/apply_claim_review_decisions.py"),
                "--review-map", str(PATHS["map"]), "--decision-packet", str(decision_path),
                "--crosswalk", str(PATHS["crosswalk"]), "--knowledge-base", str(PATHS["kb"]),
                "--components", str(PATHS["components"]), "--fallbacks", str(PATHS["fallbacks"]),
                "--fallback-reviews", str(PATHS["fallback_reviews"]),
                "--output", str(output), "--snapshot-output", str(snapshot),
                "--report-output", str(report), "--applied-date", "2026-09-10",
            ]
            process = subprocess.run(command, capture_output=True, text=True, env=environment)
            self.assertEqual(process.returncode, 0, process.stderr)
            expected_map, expected_report = self.apply(decisions)
            self.assertEqual(snapshot.read_bytes(), self.raw["map"])
            self.assertEqual(output.read_bytes(), canonical_json_bytes(expected_map))
            self.assertEqual(report.read_bytes(), canonical_json_bytes(expected_report))
            self.assertIn("changed=1 completed=31 curated=19 dry_run=False", process.stdout)

    def test_public_cli_dry_run_writes_nothing(self):
        decisions = self.decision_packet()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decision_path = root / "decisions.json"
            decision_path.write_bytes(canonical_json_bytes(decisions))
            outputs = [root / name for name in ("map.json", "snapshot.json", "report.json")]
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(SRC)
            process = subprocess.run([
                sys.executable, str(INGESTION / "scripts/apply_claim_review_decisions.py"),
                "--review-map", str(PATHS["map"]), "--decision-packet", str(decision_path),
                "--crosswalk", str(PATHS["crosswalk"]), "--knowledge-base", str(PATHS["kb"]),
                "--components", str(PATHS["components"]), "--fallbacks", str(PATHS["fallbacks"]),
                "--fallback-reviews", str(PATHS["fallback_reviews"]),
                "--output", str(outputs[0]), "--snapshot-output", str(outputs[1]),
                "--report-output", str(outputs[2]), "--applied-date", "2026-09-10", "--dry-run",
            ], capture_output=True, text=True, env=environment)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertTrue(all(not path.exists() for path in outputs))
            self.assertIn("dry_run=True", process.stdout)

    def test_public_cli_refuses_to_overwrite_snapshot(self):
        decisions = self.decision_packet()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            decision_path = root / "decisions.json"
            decision_path.write_bytes(canonical_json_bytes(decisions))
            snapshot = root / "snapshot.json"
            snapshot.write_text("preserve me")
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(SRC)
            process = subprocess.run([
                sys.executable, str(INGESTION / "scripts/apply_claim_review_decisions.py"),
                "--review-map", str(PATHS["map"]), "--decision-packet", str(decision_path),
                "--crosswalk", str(PATHS["crosswalk"]), "--knowledge-base", str(PATHS["kb"]),
                "--components", str(PATHS["components"]), "--fallbacks", str(PATHS["fallbacks"]),
                "--fallback-reviews", str(PATHS["fallback_reviews"]),
                "--output", str(root / "map.json"), "--snapshot-output", str(snapshot),
                "--report-output", str(root / "report.json"), "--applied-date", "2026-09-10",
            ], capture_output=True, text=True, env=environment)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(snapshot.read_text(), "preserve me")
            self.assertIn("refusing to overwrite", process.stderr)


if __name__ == "__main__":
    unittest.main()