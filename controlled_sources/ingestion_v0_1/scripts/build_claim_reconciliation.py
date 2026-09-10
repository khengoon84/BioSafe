#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.claim_reconciliation import (
    build_claim_reconciliation_artifacts,
    write_json_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build offline Phase C2 claim-review artifacts.")
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--knowledge-base", required=True, type=Path)
    parser.add_argument("--component-artifact", required=True, type=Path)
    parser.add_argument("--fallback-artifact", required=True, type=Path)
    parser.add_argument("--fallback-review-packet", required=True, type=Path)
    parser.add_argument("--review-packet-output", required=True, type=Path)
    parser.add_argument("--curated-kb-output", required=True, type=Path)
    args = parser.parse_args()
    kb_bytes = args.knowledge_base.read_bytes()
    component_bytes = args.component_artifact.read_bytes()
    fallback_bytes = args.fallback_artifact.read_bytes()
    fallback_review_bytes = args.fallback_review_packet.read_bytes()
    crosswalk_bytes = args.crosswalk.read_bytes()
    packet, curated = build_claim_reconciliation_artifacts(
        json.loads(crosswalk_bytes), crosswalk_bytes,
        json.loads(args.review_map.read_text(encoding="utf-8")),
        json.loads(kb_bytes), kb_bytes,
        json.loads(component_bytes), component_bytes,
        json.loads(fallback_bytes), fallback_bytes,
        json.loads(fallback_review_bytes), fallback_review_bytes,
    )
    write_json_atomic(packet, args.review_packet_output)
    write_json_atomic(curated, args.curated_kb_output)
    print(
        f"claim_reviews={packet['required_review_count']} "
        f"completed={packet['completed_review_count']} curated={packet['curated_claim_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())