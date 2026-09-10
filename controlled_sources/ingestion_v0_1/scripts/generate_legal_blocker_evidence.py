#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

from biosafe_controlled_ingestion.legal_blocker_evidence import build_legal_blocker_evidence


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate evidence-only legal blocker bundles.")
    parser.add_argument("--legal-draft", required=True, type=Path)
    parser.add_argument("--review-map", required=True, type=Path)
    parser.add_argument("--components", required=True, type=Path)
    parser.add_argument("--source-policy", required=True, type=Path)
    parser.add_argument("--source-register", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--generated-date", required=True)
    args = parser.parse_args()
    raw = {
        "draft": args.legal_draft.read_bytes(),
        "map": args.review_map.read_bytes(),
        "components": args.components.read_bytes(),
        "policy": args.source_policy.read_bytes(),
        "register": args.source_register.read_bytes(),
    }
    register = list(csv.DictReader(
        io.StringIO(raw["register"].decode("utf-8")), delimiter="\t"
    ))
    bundles, index = build_legal_blocker_evidence(
        json.loads(raw["draft"]), raw["draft"],
        json.loads(raw["map"]), raw["map"],
        json.loads(raw["components"]), raw["components"],
        json.loads(raw["policy"]), raw["policy"],
        register, raw["register"], args.generated_date,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for claim_id, content in bundles.items():
        (args.output_dir / f"legal_blocker_{claim_id}.md").write_text(content, encoding="utf-8")
    (args.output_dir / "INDEX.md").write_text(index, encoding="utf-8")
    print(f"bundles={len(bundles)} claims={','.join(sorted(bundles))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())