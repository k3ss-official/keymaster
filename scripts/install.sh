#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Installing Keymaster (editable + dev extras)"

python3 -m pip install -e ".[dev]"

echo "==> Installing Playwright Chromium"
python3 -m playwright install chromium

if ! command -v op &>/dev/null; then
  echo "WARNING: 1Password CLI (op) not found — install from https://1password.com/downloads/command-line/"
fi

if ! command -v gpg &>/dev/null; then
  echo "WARNING: gpg not found — glass-break encrypted backups will fail until GnuPG is installed"
fi

mkdir -p logs

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example — fill in values before rotating"
else
  echo "==> .env already present"
fi

echo "==> Done."
echo "    python keymaster.py --list-providers"
echo "    python keymaster.py --audit"
echo "    python keymaster.py --rotate --dry-run"
