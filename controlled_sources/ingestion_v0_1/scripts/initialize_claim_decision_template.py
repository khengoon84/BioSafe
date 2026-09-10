#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.claim_decision_entry import canonical_json_bytes, write_bytes_atomic
from biosafe_controlled_ingestion.claim_decision_template import initialize_decision_template


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize an incomplete human claim-review packet.")
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--review-aid", required=True, type=Path)
    parser.add_argument("--claim-id", required=True, action="append")
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--packet-output", required=True, type=Path)
    parser.add_argument("--worksheet-output", required=True, type=Path)
    args = parser.parse_args()
    map_bytes = args.review_map.read_bytes()
    aid_bytes = args.review_aid.read_bytes()
    packet, worksheet = initialize_decision_template(
        json.loads(map_bytes), map_bytes, json.loads(aid_bytes), aid_bytes,
        sorted(args.claim_id), args.batch_id,
    )
    write_bytes_atomic(canonical_json_bytes(packet), args.packet_output)
    write_bytes_atomic(worksheet.encode("utf-8"), args.worksheet_output)
    print(f"batch={args.batch_id} claims={len(packet['claim_ids'])} human_review_status=HUMAN_REVIEW_REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())