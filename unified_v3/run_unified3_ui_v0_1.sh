#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Unified-3 Ask BioSafe UI"
echo "  UI:       http://127.0.0.1:${UI_PORT:-8778}"
echo "  Sidecar:  http://127.0.0.1:8777"
echo ""
exec "$ROOT/.venv/bin/python" "$ROOT/unified_v3/server_ui_v0_1.py"
