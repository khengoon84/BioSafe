#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.legal_claim_review_draft import (
    build_legal_claim_review_draft,
    write_legal_claim_review_draft,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the offline nine-claim legal review draft aid.")
    parser.add_argument("--draft-map", required=True, type=Path)
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--source-policy", required=True, type=Path)
    parser.add_argument("--component-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    draft_bytes = args.draft_map.read_bytes()
    review_bytes = args.review_map.read_bytes()
    policy_bytes = args.source_policy.read_bytes()
    component_bytes = args.component_artifact.read_bytes()
    artifact = build_legal_claim_review_draft(
        json.loads(draft_bytes), draft_bytes,
        json.loads(review_bytes), review_bytes,
        json.loads(policy_bytes), policy_bytes,
        json.loads(component_bytes), component_bytes,
    )
    write_legal_claim_review_draft(artifact, args.output)
    print(f"legal_claims={artifact['legal_claim_count']} draft_dispositions={artifact['draft_dispositions_present']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())