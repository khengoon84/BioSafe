#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from biosafe_controlled_ingestion.contracts import ExtractionStatus
from biosafe_controlled_ingestion.preflight import load_source_register
from biosafe_controlled_ingestion.pypdf_extractor import extract_documents, write_extraction_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract page records into an offline BioSafe artifact.")
    parser.add_argument("--staging-dir", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--document-id", action="append")
    selection.add_argument("--all-eligible", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    records = load_source_register(args.staging_dir / "SOURCE_REGISTER.tsv", args.policy)
    document_ids = (
        [record.document_id for record in records if record.extraction_eligibility.value == "ELIGIBLE_FOR_OFFLINE_EXTRACTION"]
        if args.all_eligible
        else args.document_id
    )
    report = extract_documents(records, args.staging_dir, document_ids)
    write_extraction_report(report, args.output)
    for document in report.documents:
        print(
            f"{document.document_id}: status={document.status.value} "
            f"pages={document.extracted_page_count}/{document.pdf_page_count} "
            f"nonempty={document.nonempty_page_count} characters={document.total_characters}"
        )
    blocked = {
        ExtractionStatus.INVALID_SOURCE,
        ExtractionStatus.BLOCKED_ENCRYPTED,
        ExtractionStatus.BLOCKED_SIZE_LIMIT,
        ExtractionStatus.BLOCKED_SOURCE_VERIFICATION,
    }
    return 2 if any(document.status in blocked for document in report.documents) else 0


if __name__ == "__main__":
    raise SystemExit(main())