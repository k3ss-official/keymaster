#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing Keymaster dependencies"

# 1. Python deps
pip install -e .[dev]

# 2. Playwright browser
playwright install chromium

# 3. Check op CLI
if ! command -v op &>/dev/null; then
  echo "WARNING: 1Password CLI (op) not found — install from https://1password.com/downloads/command-line/"
fi

echo "==> Done.  Copy .env.example → .env and fill in values."
