#!/usr/bin/env bash
set -euo pipefail

echo "=== BioSafe WSL2 Development Environment v0.1 ==="

if ! grep -qi microsoft /proc/version; then
  echo "WARNING: WSL was not detected. Continuing as Linux."
fi

echo "[1/6] Updating apt metadata..."
sudo apt-get update

echo "[2/6] Installing core tools..."
sudo apt-get install -y python3 python3-venv python3-pip git curl build-essential

echo "[3/6] Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "[4/6] Upgrading pip..."
python -m pip install --upgrade pip

echo "[5/6] Installing BioSafe Python requirements..."
python -m pip install -r requirements.txt

echo "[6/6] Running preflight..."
bash scripts/preflight.sh

echo
echo "Setup complete."
echo "Activate later with: source .venv/bin/activate"
echo "Open in VS Code with: code ."
