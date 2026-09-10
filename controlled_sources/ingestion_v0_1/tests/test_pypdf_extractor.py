from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "controlled_sources/ingestion_v0_1/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from biosafe_controlled_ingestion.contracts import (  # noqa: E402
    ExtractionStatus,
    SourceRecord,
    SourceStatus,
    ValidationError,
)
from biosafe_controlled_ingestion.pypdf_extractor import (  # noqa: E402
    _extract_page_text,
    extract_document,
    extract_documents,
    write_extraction_report,
)


class WarningPage:
    def extract_text(self, extraction_mode):
        self.extraction_mode = extraction_mode
        logging.getLogger("pypdf").warning("Rotated text discovered. Output will be incomplete.")
        return "Extracted text\r\n"


class FontWarningPage:
    def extract_text(self, extraction_mode):
        logger = logging.getLogger("pypdf")
        logger.warning("Advanced encoding /SymbolSetEncoding not implemented yet")
        logger.warning("fontTools is required to fully parse the encoding of a CFF Type1 font in font dictionary {...}, but is not installed.")
        return "Text"


class PypdfExtractorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.pdf = self.base / "source.pdf"
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.add_blank_page(width=612, height=792)
        with self.pdf.open("wb") as handle:
            writer.write(handle)
        os.chmod(self.pdf, 0o644)
        raw = self.pdf.read_bytes()
        self.record = SourceRecord(
            document_id="D1",
            staged_filename=self.pdf.name,
            source_sha256=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
            title="Test PDF",
            publisher="Test Publisher",
            jurisdiction="International",
            authority_tier=3,
            document_type="Test guidance",
            publication_date="2026",
            currentness_status="test",
            supersession_status="test",
            official_landing_page="https://example.test/page",
            direct_download_url="https://example.test/source.pdf",
            allowed_domains=("test",),
            excluded_domains=("law",),
            extraction_eligibility=SourceStatus.ELIGIBLE_FOR_OFFLINE_EXTRACTION,
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_blank_pages_are_retained_and_warned(self):
        result = extract_document(self.record, self.base)
        self.assertEqual(result.status, ExtractionStatus.EXTRACTED_WITH_WARNINGS)
        self.assertEqual(result.pdf_page_count, 2)
        self.assertEqual(result.extracted_page_count, 2)
        self.assertEqual(result.nonempty_page_count, 0)
        self.assertEqual([page.pdf_page_index for page in result.pages], [1, 2])
        self.assertTrue(all("PAGE_TEXT_EMPTY_POSSIBLE_SCAN_OR_DECORATIVE_PAGE" in page.extraction_warnings for page in result.pages))
        self.assertTrue(all(page.pdf_page_label for page in result.pages))
        self.assertTrue(all(page.printed_page_label == "" for page in result.pages))
        self.assertIn("PRINTED_PAGE_LABELS_NOT_VISUALLY_VERIFIED", result.warnings)

    def test_pypdf_rotated_text_warning_is_structured(self):
        page = WarningPage()
        text, warnings = _extract_page_text(page)
        self.assertEqual(page.extraction_mode, "layout")
        self.assertEqual(text, "Extracted text")
        self.assertEqual(warnings, ("ROTATED_TEXT_OMITTED_BY_LAYOUT_MODE",))

    def test_font_warnings_are_normalized_without_internal_ids(self):
        text, warnings = _extract_page_text(FontWarningPage())
        self.assertEqual(text, "Text")
        self.assertEqual(
            warnings,
            (
                "FONT_ENCODING_SYMBOLSET_UNSUPPORTED",
                "FONT_ENCODING_CFF_REQUIRES_FONTTOOLS",
            ),
        )

    def test_held_source_is_blocked_before_reading(self):
        held = SourceRecord(**{**self.record.__dict__, "extraction_eligibility": SourceStatus.HOLD_SOURCE_VERIFICATION})
        result = extract_document(held, self.base)
        self.assertEqual(result.status, ExtractionStatus.BLOCKED_SOURCE_VERIFICATION)
        self.assertEqual(result.extracted_page_count, 0)

    def test_changed_hash_is_invalid(self):
        self.pdf.write_bytes(self.pdf.read_bytes() + b"tamper")
        result = extract_document(self.record, self.base)
        self.assertEqual(result.status, ExtractionStatus.INVALID_SOURCE)
        self.assertIn("source size changed", result.warnings[0])

    def test_size_limit_blocks_before_parser(self):
        result = extract_document(self.record, self.base, max_source_bytes=1)
        self.assertEqual(result.status, ExtractionStatus.BLOCKED_SIZE_LIMIT)

    def test_empty_password_encrypted_pdf_is_extracted_with_warning(self):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt(user_password="", owner_password="owner")
        with self.pdf.open("wb") as handle:
            writer.write(handle)
        raw = self.pdf.read_bytes()
        record = SourceRecord(**{
            **self.record.__dict__,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        })
        result = extract_document(record, self.base)
        self.assertEqual(result.extracted_page_count, 1)
        self.assertIn("PDF_DECRYPTED_WITH_EMPTY_PASSWORD", result.warnings)

    def test_nonempty_password_encrypted_pdf_is_blocked(self):
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.encrypt(user_password="secret", owner_password="owner")
        with self.pdf.open("wb") as handle:
            writer.write(handle)
        raw = self.pdf.read_bytes()
        record = SourceRecord(**{
            **self.record.__dict__,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw),
        })
        result = extract_document(record, self.base)
        self.assertEqual(result.status, ExtractionStatus.BLOCKED_ENCRYPTED)
        self.assertEqual(result.extracted_page_count, 0)
        self.assertIn("ENCRYPTED_PDF_REQUIRES_NONEMPTY_PASSWORD", result.warnings)

    def test_unknown_document_id_is_rejected(self):
        with self.assertRaisesRegex(ValidationError, "unknown document IDs"):
            extract_documents([self.record], self.base, ["MISSING"])

    def test_duplicate_requested_ids_are_deduplicated(self):
        report = extract_documents([self.record], self.base, ["D1", "D1"])
        self.assertEqual(report.requested_document_ids, ("D1",))
        self.assertEqual(len(report.documents), 1)

    def test_json_output_is_stable_and_offline(self):
        report = extract_documents([self.record], self.base, ["D1"])
        output = self.base / "out" / "pages.json"
        write_extraction_report(report, output)
        first = output.read_bytes()
        write_extraction_report(report, output)
        self.assertEqual(first, output.read_bytes())
        payload = json.loads(first)
        self.assertEqual(payload["live_activation_status"], "PROHIBITED_PENDING_PHASE_C_GATES")
        self.assertEqual(payload["documents"][0]["pdf_page_count"], 2)


if __name__ == "__main__":
    unittest.main()