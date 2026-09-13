#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.exact_support_review import (
    accept_source_support_review,
    write_exact_support_review_packet,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Record human acceptance of exact source support without claim promotion.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reviewer-identity", required=True)
    parser.add_argument("--reviewer-role", required=True)
    parser.add_argument("--review-date", required=True)
    args = parser.parse_args()
    packet = accept_source_support_review(
        json.loads(args.input.read_text(encoding="utf-8")),
        reviewer_identity=args.reviewer_identity,
        reviewer_role=args.reviewer_role,
        review_date=args.review_date,
    )
    write_exact_support_review_packet(packet, args.output)
    print(f"claims={len(packet['entries'])} human_review_status={packet['human_review_status']} promotion={packet['promotion_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())