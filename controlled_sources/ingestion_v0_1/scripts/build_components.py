#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.components import (
    build_component_artifact,
    build_review_ledger,
    load_component_map,
    write_json_atomic,
    write_review_ledger,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build offline reviewed-boundary component candidates.")
    parser.add_argument("--pages", required=True, type=Path)
    parser.add_argument("--component-map", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ledger-output", required=True, type=Path)
    args = parser.parse_args()
    extraction_report = json.loads(args.pages.read_text(encoding="utf-8"))
    component_map, policies = load_component_map(args.component_map)
    artifact = build_component_artifact(extraction_report, policies)
    ledger = build_review_ledger(extraction_report, component_map)
    write_json_atomic(artifact, args.output)
    write_review_ledger(ledger, args.ledger_output)
    print(
        f"components={len(artifact['components'])} "
        f"candidate_chunks={len(artifact['candidate_chunks'])} "
        f"ledger_rows={len(ledger)} activation={artifact['live_activation_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())