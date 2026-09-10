#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.claim_decision_entry import (
    apply_claim_decisions,
    canonical_json_bytes,
    write_bytes_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and apply human claim-review decisions.")
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--decision-packet", required=True, type=Path)
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--knowledge-base", required=True, type=Path)
    parser.add_argument("--components", required=True, type=Path)
    parser.add_argument("--fallbacks", required=True, type=Path)
    parser.add_argument("--fallback-reviews", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--snapshot-output", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    parser.add_argument("--applied-date", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    paths = {
        "map": args.review_map, "decisions": args.decision_packet,
        "crosswalk": args.crosswalk, "kb": args.knowledge_base,
        "components": args.components, "fallbacks": args.fallbacks,
        "fallback_reviews": args.fallback_reviews,
    }
    raw = {name: path.read_bytes() for name, path in paths.items()}
    data = {name: json.loads(value) for name, value in raw.items()}
    result, report = apply_claim_decisions(
        data["map"], raw["map"], data["decisions"], raw["decisions"],
        data["crosswalk"], raw["crosswalk"], data["kb"], raw["kb"],
        data["components"], raw["components"], data["fallbacks"], raw["fallbacks"],
        data["fallback_reviews"], raw["fallback_reviews"], args.applied_date,
    )
    if not args.dry_run:
        output_paths = {
            args.output.resolve(), args.snapshot_output.resolve(), args.report_output.resolve()
        }
        if len(output_paths) != 3:
            raise ValueError("map, snapshot, and report output paths must be distinct")
        if args.snapshot_output.exists():
            raise FileExistsError("snapshot output already exists; refusing to overwrite evidence")
        if args.report_output.exists():
            raise FileExistsError("report output already exists; refusing to overwrite evidence")
        write_bytes_atomic(raw["map"], args.snapshot_output)
        write_bytes_atomic(canonical_json_bytes(result), args.output)
        write_bytes_atomic(canonical_json_bytes(report), args.report_output)
    print(
        f"batch={report['batch_id']} changed={report['changed_claim_count']} "
        f"completed={report['total_completed_review_count']} "
        f"curated={report['total_curated_claim_count']} dry_run={args.dry_run}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())