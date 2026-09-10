#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.fallback_human_review import (
    build_fallback_human_review_packet,
    write_fallback_human_review_packet,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an offline source-bound semantic-fallback human-review packet."
    )
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--fallback-artifact", required=True, type=Path)
    parser.add_argument("--render-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    fallback_bytes = args.fallback_artifact.read_bytes()
    packet = build_fallback_human_review_packet(
        json.loads(args.review_map.read_text(encoding="utf-8")),
        json.loads(fallback_bytes),
        fallback_bytes,
        json.loads(args.render_manifest.read_text(encoding="utf-8")),
    )
    write_fallback_human_review_packet(packet, args.output)
    print(
        f"review_items={packet['required_review_count']} "
        f"completed={packet['completed_review_count']} "
        f"status={packet['review_completion_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())