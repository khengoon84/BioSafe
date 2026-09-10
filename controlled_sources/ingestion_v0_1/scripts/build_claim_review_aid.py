#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import io
from pathlib import Path

from biosafe_controlled_ingestion.claim_review_aid import build_claim_review_aid, write_claim_review_aid


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the offline Phase C2 navigation-only review aid.")
    parser.add_argument("--crosswalk", required=True, type=Path)
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--knowledge-base", required=True, type=Path)
    parser.add_argument("--source-policy", required=True, type=Path)
    parser.add_argument("--source-register", required=True, type=Path)
    parser.add_argument("--component-artifact", required=True, type=Path)
    parser.add_argument("--fallback-artifact", required=True, type=Path)
    parser.add_argument("--fallback-review-packet", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    paths = {
        "crosswalk": args.crosswalk, "review_map": args.review_map,
        "knowledge_base": args.knowledge_base, "source_policy": args.source_policy,
        "source_register": args.source_register,
        "component_artifact": args.component_artifact, "fallback_artifact": args.fallback_artifact,
        "fallback_review_packet": args.fallback_review_packet,
    }
    raw = {name: path.read_bytes() for name, path in paths.items()}
    parsed = {
        name: json.loads(value)
        for name, value in raw.items()
        if name != "source_register"
    }
    parsed["source_register"] = list(csv.DictReader(
        io.StringIO(raw["source_register"].decode("utf-8")), delimiter="\t"
    ))
    aid = build_claim_review_aid(
        parsed["crosswalk"], raw["crosswalk"], parsed["review_map"], raw["review_map"],
        parsed["knowledge_base"], raw["knowledge_base"], parsed["source_policy"], raw["source_policy"],
        parsed["source_register"], raw["source_register"],
        parsed["component_artifact"], raw["component_artifact"],
        parsed["fallback_artifact"], raw["fallback_artifact"],
        parsed["fallback_review_packet"], raw["fallback_review_packet"],
    )
    write_claim_review_aid(aid, args.output)
    print(
        f"identity_mappings={aid['identity_mapping_item_count']} "
        f"identity_pending={aid['pending_identity_review_count']} "
        f"claim_reviews={aid['claim_review_item_count']} "
        f"claim_pending={aid['pending_claim_review_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())