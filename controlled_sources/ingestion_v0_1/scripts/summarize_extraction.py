#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def build_summary(report: dict) -> dict:
    documents = []
    total_pages = 0
    total_nonempty = 0
    total_characters = 0
    aggregate_warnings: Counter[str] = Counter()
    for document in report["documents"]:
        warning_counts: Counter[str] = Counter()
        warning_pages: dict[str, list[int]] = {}
        for page in document["pages"]:
            for warning in page["extraction_warnings"]:
                warning_counts[warning] += 1
                warning_pages.setdefault(warning, []).append(page["pdf_page_index"])
        total_pages += document["pdf_page_count"]
        total_nonempty += document["nonempty_page_count"]
        total_characters += document["total_characters"]
        aggregate_warnings.update(warning_counts)
        documents.append({
            "document_id": document["document_id"],
            "status": document["status"],
            "source_sha256": document["source_sha256"],
            "pdf_page_count": document["pdf_page_count"],
            "extracted_page_count": document["extracted_page_count"],
            "nonempty_page_count": document["nonempty_page_count"],
            "total_characters": document["total_characters"],
            "warning_counts": dict(sorted(warning_counts.items())),
            "warning_pages": {key: value for key, value in sorted(warning_pages.items())},
        })
    return {
        "summary_version": "BioSafe_Extraction_Quality_Summary_v0.1",
        "source_report_version": report["report_version"],
        "parser": report["parser"],
        "live_activation_status": report["live_activation_status"],
        "document_count": len(documents),
        "total_pdf_pages": total_pages,
        "total_nonempty_pages": total_nonempty,
        "total_characters": total_characters,
        "aggregate_page_warning_counts": dict(sorted(aggregate_warnings.items())),
        "documents": documents,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a BioSafe offline page-extraction report.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = json.loads(args.input.read_text(encoding="utf-8"))
    summary = build_summary(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"documents={summary['document_count']}")
    print(f"pages={summary['total_pdf_pages']}")
    print(f"nonempty={summary['total_nonempty_pages']}")
    print(f"characters={summary['total_characters']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())