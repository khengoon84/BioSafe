#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.exact_support_review import (
    build_exact_support_review_packet,
    write_exact_support_review_packet,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the offline exact-support review packet for CLM-005 and CLM-007.")
    parser.add_argument("--component-artifact", required=True, type=Path)
    parser.add_argument("--amendment-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    component_bytes = args.component_artifact.read_bytes()
    amendment_bytes = args.amendment_artifact.read_bytes()
    packet = build_exact_support_review_packet(
        json.loads(component_bytes), component_bytes,
        amendment_artifact=json.loads(amendment_bytes), amendment_artifact_bytes=amendment_bytes,
    )
    write_exact_support_review_packet(packet, args.output)
    print(f"claims={len(packet['entries'])} human_review_status={packet['human_review_status']} promotion={packet['promotion_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())