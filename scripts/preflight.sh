#!/usr/bin/env bash
set -euo pipefail

echo "=== BioSafe WSL2 Preflight ==="
echo "User: $USER"
echo "Home: $HOME"
echo "Project: $(pwd)"
echo

if grep -qi microsoft /proc/version; then
  echo "[OK] WSL detected"
else
  echo "[WARN] This does not appear to be WSL."
fi

echo -n "Python: "
python3 --version

echo -n "Git: "
git --version

echo
python3 scripts/detect_ollama.py || true

echo
if [ -d ".venv" ]; then
  echo "[OK] .venv exists"
else
  echo "[WARN] .venv not found. Run: ./scripts/setup_wsl2.sh"
fi
