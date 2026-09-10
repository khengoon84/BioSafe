from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/summarize_extraction.py"
SPEC = importlib.util.spec_from_file_location("summarize_extraction", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExtractionSummaryTests(unittest.TestCase):
    def test_warning_counts_and_pages_are_preserved(self):
        report = {
            "report_version": "test",
            "parser": "pypdf==test",
            "live_activation_status": "PROHIBITED_PENDING_PHASE_C_GATES",
            "documents": [
                {
                    "document_id": "D1", "status": "EXTRACTED_WITH_WARNINGS",
                    "source_sha256": "a" * 64, "pdf_page_count": 2,
                    "extracted_page_count": 2, "nonempty_page_count": 1,
                    "total_characters": 10,
                    "pages": [
                        {"pdf_page_index": 1, "extraction_warnings": ["LOW"]},
                        {"pdf_page_index": 2, "extraction_warnings": ["EMPTY", "LOW"]},
                    ],
                }
            ],
        }
        summary = MODULE.build_summary(report)
        self.assertEqual(summary["document_count"], 1)
        self.assertEqual(summary["total_pdf_pages"], 2)
        self.assertEqual(summary["aggregate_page_warning_counts"], {"EMPTY": 1, "LOW": 2})
        self.assertEqual(summary["documents"][0]["warning_pages"]["LOW"], [1, 2])
        self.assertEqual(summary["live_activation_status"], "PROHIBITED_PENDING_PHASE_C_GATES")


if __name__ == "__main__":
    unittest.main()