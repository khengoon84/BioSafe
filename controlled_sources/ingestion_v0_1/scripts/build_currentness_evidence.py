#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from biosafe_controlled_ingestion.currentness_review import (
    build_currentness_evidence_packet,
    write_currentness_evidence_packet,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build targeted offline currentness evidence for CLM-005 and CLM-007.")
    parser.add_argument("--source-register", required=True, type=Path)
    parser.add_argument("--source-policy", required=True, type=Path)
    parser.add_argument("--amendment-artifact", required=True, type=Path)
    parser.add_argument("--exact-support-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    register_bytes = args.source_register.read_bytes()
    policy_bytes = args.source_policy.read_bytes()
    amendment_bytes = args.amendment_artifact.read_bytes()
    support_bytes = args.exact_support_artifact.read_bytes()
    with args.source_register.open(encoding="utf-8", newline="") as stream:
        register = list(csv.DictReader(stream, delimiter="\t"))
    packet = build_currentness_evidence_packet(
        register, register_bytes, json.loads(policy_bytes), policy_bytes,
        json.loads(amendment_bytes), amendment_bytes,
        json.loads(support_bytes), support_bytes,
    )
    write_currentness_evidence_packet(packet, args.output)
    print(f"provisions={len(packet['provisions'])} human_review_status={packet['human_review_status']} promotion={packet['promotion_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())