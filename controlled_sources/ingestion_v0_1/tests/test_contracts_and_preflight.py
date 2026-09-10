from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "controlled_sources/ingestion_v0_1/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from biosafe_controlled_ingestion.contracts import (  # noqa: E402
    ChunkRecord,
    ExtractionStatus,
    SourceRecord,
    SourceStatus,
    ValidationError,
)
from biosafe_controlled_ingestion.preflight import (  # noqa: E402
    load_source_register,
    run_preflight,
    write_report,
)


def valid_pdf() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\nstartxref\n0\n%%EOF\n"


class ContractTests(unittest.TestCase):
    def test_act_678_local_file_is_the_sole_canonical_biosafe_source(self):
        ingestion = ROOT / "controlled_sources/ingestion_v0_1"
        policy = json.loads(
            (ingestion / "config/source_policy_v0_1.json").read_text(encoding="utf-8")
        )["sources"]["KB-MY-ACT678"]
        with (ROOT / "controlled_sources/staging_v0_1/SOURCE_REGISTER.tsv").open(
            newline="", encoding="utf-8"
        ) as handle:
            records = [
                row for row in csv.DictReader(handle, delimiter="\t")
                if row["candidate_id"] == "KB-MY-ACT678"
            ]
        self.assertEqual(len(records), 1)
        record = records[0]
        canonical_hash = "8c2badc2db503906b92a42b905736653b868ee3c7bc6fb79719e0081cf25e8cc"
        self.assertEqual(record["sha256"], canonical_hash)
        self.assertEqual(
            hashlib.sha256(
                (ROOT / "controlled_sources/staging_v0_1" / record["staged_filename"]).read_bytes()
            ).hexdigest(),
            canonical_hash,
        )
        self.assertEqual(record["status"], "STAGED_OWNER_DESIGNATED_SOLE_CANONICAL_BIOSAFE_SOURCE")
        self.assertEqual(
            policy["currentness_status"],
            "OWNER_DESIGNATED_SOLE_CANONICAL_BIOSAFE_SOURCE_AMENDMENT_REVIEW_REQUIRED",
        )
        self.assertEqual(
            policy["supersession_status"],
            "AMENDMENT_AND_CLAIM_LEVEL_CURRENTNESS_REVIEW_REQUIRED",
        )
        self.assertEqual(record["live_activation_status"], "PROHIBITED_PENDING_PHASE_C_GATES")
        self.assertNotIn(
            "196ac44261e3e18e357f055ba232f3b1cee6dbc01b501918678032e2e3fb779c",
            json.dumps(policy),
        )

    def test_source_rejects_domain_overlap(self):
        record = SourceRecord(
            "D1", "a.pdf", "a" * 64, 10, "Title", "Publisher", "International", 3,
            "guidance", "2020", "current", "none", "https://example.test/page",
            "https://example.test/a.pdf", ("risk",), ("risk",),
            SourceStatus.ELIGIBLE_FOR_OFFLINE_EXTRACTION,
        )
        with self.assertRaisesRegex(ValidationError, "must not overlap"):
            record.validate()

    def test_chunk_rejects_invalid_page_range(self):
        chunk = ChunkRecord(
            "C1", "D1", "a" * 64, "Title", "Publisher", "International", 3,
            "guidance", "2020", "current", "none", "", "", "", "Heading",
            3, 2, "", "", "Context", "Text", ("risk",), "risk_principle",
            "https://example.test/a.pdf", "test", "2026-09-08T00:00:00Z",
        )
        with self.assertRaisesRegex(ValidationError, "page range"):
            chunk.validate()


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.staging = self.base / "staging"
        self.staging.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def _write_fixture(self, eligibility="ELIGIBLE_FOR_OFFLINE_EXTRACTION", second=False):
        raw = valid_pdf()
        rows = []
        for index, name in enumerate(["one.pdf", "two.pdf"] if second else ["one.pdf"], 1):
            (self.staging / name).write_bytes(raw)
            os.chmod(self.staging / name, 0o644)
            rows.append({
                "candidate_id": f"D{index}", "staged_filename": name,
                "size_bytes": str(len(raw)), "sha256": hashlib.sha256(raw).hexdigest(),
                "title": "", "publisher": "", "publication_date": "",
                "official_landing_page": "", "direct_download_url": "",
                "expected_document_type": "",
            })
        fields = list(rows[0])
        with (self.staging / "SOURCE_REGISTER.tsv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fields, delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
        policy = {"sources": {}}
        for index in range(1, len(rows) + 1):
            policy["sources"][f"D{index}"] = {
                "title": "Title", "publisher": "Publisher", "jurisdiction": "International",
                "authority_tier": 3, "document_type": "guidance", "publication_date": "2020",
                "currentness_status": "current", "supersession_status": "none",
                "official_landing_page": "https://example.test/page",
                "direct_download_url": "https://example.test/file.pdf",
                "allowed_domains": ["risk"], "excluded_domains": ["law"],
                "extraction_eligibility": eligibility,
            }
        self.policy = self.base / "policy.json"
        self.policy.write_text(json.dumps(policy), encoding="utf-8")
        return raw

    def test_register_requires_policy_for_every_source(self):
        self._write_fixture()
        self.policy.write_text('{"sources": {}}', encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "missing source policy"):
            load_source_register(self.staging / "SOURCE_REGISTER.tsv", self.policy)

    @patch("biosafe_controlled_ingestion.preflight.detect_extraction_backend", return_value="unavailable")
    def test_unavailable_backend_blocks_without_writing(self, _mocked):
        self._write_fixture()
        before = sorted(path.name for path in self.staging.iterdir())
        report = run_preflight(self.staging, self.policy)
        after = sorted(path.name for path in self.staging.iterdir())
        self.assertEqual(report.overall_status, ExtractionStatus.BLOCKED_EXTRACTOR_UNAVAILABLE)
        self.assertEqual(report.checks[0].status, ExtractionStatus.BLOCKED_EXTRACTOR_UNAVAILABLE)
        self.assertEqual(before, after)

    @patch("biosafe_controlled_ingestion.preflight.detect_extraction_backend", return_value="python:pypdf")
    def test_source_verification_hold_blocks_extraction(self, _mocked):
        self._write_fixture(eligibility="HOLD_SOURCE_VERIFICATION")
        report = run_preflight(self.staging, self.policy)
        self.assertEqual(report.overall_status, ExtractionStatus.BLOCKED_SOURCE_VERIFICATION)

    @patch("biosafe_controlled_ingestion.preflight.detect_extraction_backend", return_value="unavailable")
    def test_source_hold_and_backend_block_are_both_reported(self, _mocked):
        self._write_fixture(eligibility="HOLD_SOURCE_VERIFICATION")
        report = run_preflight(self.staging, self.policy)
        self.assertEqual(report.overall_status, ExtractionStatus.BLOCKED_SOURCE_VERIFICATION)
        self.assertEqual(
            report.warnings,
            (
                "BLOCKED_SOURCE_VERIFICATION",
                "BLOCKED_EXTRACTOR_UNAVAILABLE",
            ),
        )

    @patch("biosafe_controlled_ingestion.preflight.detect_extraction_backend", return_value="python:pypdf")
    def test_hash_mismatch_is_invalid(self, _mocked):
        self._write_fixture()
        (self.staging / "one.pdf").write_bytes(valid_pdf() + b"tampered")
        report = run_preflight(self.staging, self.policy)
        self.assertEqual(report.overall_status, ExtractionStatus.INVALID_SOURCE)

    @patch("biosafe_controlled_ingestion.preflight.detect_extraction_backend", return_value="python:pypdf")
    def test_duplicate_hash_is_invalid(self, _mocked):
        self._write_fixture(second=True)
        report = run_preflight(self.staging, self.policy)
        self.assertEqual(report.overall_status, ExtractionStatus.INVALID_SOURCE)
        self.assertEqual(report.checks[1].duplicate_of, "D1")
        self.assertIn("DUPLICATE_SOURCE_HASH", report.checks[1].warnings)

    @patch("biosafe_controlled_ingestion.preflight.detect_extraction_backend", return_value="python:pypdf")
    def test_valid_source_is_ready_when_backend_exists(self, _mocked):
        self._write_fixture()
        report = run_preflight(self.staging, self.policy)
        self.assertEqual(report.overall_status, ExtractionStatus.READY)
        self.assertEqual(report.eligible_source_count, 1)

    @patch("biosafe_controlled_ingestion.preflight.detect_extraction_backend", return_value="unavailable")
    def test_report_serialization_is_stable(self, _mocked):
        self._write_fixture()
        report = run_preflight(self.staging, self.policy)
        output = self.base / "reports" / "report.json"
        write_report(report, output)
        first = output.read_bytes()
        write_report(report, output)
        self.assertEqual(first, output.read_bytes())
        loaded = json.loads(first)
        self.assertEqual(loaded["overall_status"], "BLOCKED_EXTRACTOR_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()