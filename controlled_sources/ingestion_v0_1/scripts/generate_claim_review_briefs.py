#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.claim_review_briefs import (
    build_claim_review_briefs,
    write_claim_review_briefs,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate navigation-only briefs for pending claim reviews."
    )
    parser.add_argument("--review-aid", required=True, type=Path)
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--generated-date", required=True)
    args = parser.parse_args()
    aid_bytes = args.review_aid.read_bytes()
    map_bytes = args.review_map.read_bytes()
    briefs, index = build_claim_review_briefs(
        json.loads(aid_bytes), aid_bytes, map_bytes,
        str(args.review_aid), str(args.review_map), args.generated_date,
    )
    write_claim_review_briefs(briefs, index, args.output_dir)
    print(
        f"briefs={len(briefs)} pending_claims="
        f"{sum(text.count('\n## CLM-') for text in briefs.values())}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())