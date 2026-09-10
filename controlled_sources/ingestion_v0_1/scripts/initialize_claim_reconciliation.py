#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.claim_reconciliation import (
    initialize_claim_reconciliation_map,
    write_json_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize the offline Phase C2 claim-review map.")
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--knowledge-base", required=True, type=Path)
    parser.add_argument("--component-artifact", required=True, type=Path)
    parser.add_argument("--fallback-artifact", required=True, type=Path)
    parser.add_argument("--fallback-review-packet", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    kb_bytes = args.knowledge_base.read_bytes()
    component_bytes = args.component_artifact.read_bytes()
    fallback_bytes = args.fallback_artifact.read_bytes()
    fallback_review_bytes = args.fallback_review_packet.read_bytes()
    crosswalk_bytes = args.crosswalk.read_bytes()
    result = initialize_claim_reconciliation_map(
        json.loads(crosswalk_bytes), crosswalk_bytes,
        json.loads(kb_bytes), kb_bytes,
        json.loads(component_bytes), component_bytes,
        fallback_bytes, fallback_review_bytes,
    )
    write_json_atomic(result, args.output)
    print(f"claim_reviews={len(result['claim_reviews'])} status={result['claim_use_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())