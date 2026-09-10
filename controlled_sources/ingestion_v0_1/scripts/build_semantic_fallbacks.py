#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from biosafe_controlled_ingestion.semantic_fallbacks import (
    build_semantic_fallback_artifact,
    write_semantic_fallback_artifact,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build offline source-bound semantic fallbacks.")
    parser.add_argument("--fallback-map", required=True, type=Path)
    parser.add_argument("--pages", required=True, type=Path)
    parser.add_argument("--render-manifest", required=True, type=Path)
    parser.add_argument("--component-artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    fallback_map = json.loads(args.fallback_map.read_text(encoding="utf-8"))
    pages = json.loads(args.pages.read_text(encoding="utf-8"))
    renders = json.loads(args.render_manifest.read_text(encoding="utf-8"))
    components = json.loads(args.component_artifact.read_text(encoding="utf-8"))
    artifact = build_semantic_fallback_artifact(fallback_map, pages, renders, components)
    write_semantic_fallback_artifact(artifact, args.output)
    print(
        f"fallback_units={len(artifact['fallback_units'])} "
        f"activation={artifact['live_activation_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())