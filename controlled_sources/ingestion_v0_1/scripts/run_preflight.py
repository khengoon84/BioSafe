#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from biosafe_controlled_ingestion.contracts import ExtractionStatus
from biosafe_controlled_ingestion.preflight import run_preflight, write_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight the disconnected BioSafe source collection.")
    parser.add_argument("--staging-dir", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = run_preflight(args.staging_dir, args.policy)
    write_report(report, args.output)
    print(f"status={report.overall_status.value}")
    print(f"sources={report.source_count}")
    print(f"eligible={report.eligible_source_count}")
    print(f"backend={report.extraction_backend}")
    return 0 if report.overall_status == ExtractionStatus.READY else 2


if __name__ == "__main__":
    raise SystemExit(main())