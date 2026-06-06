#!/usr/bin/env bash
# Rotation script invoked by launchd / cron
set -euo pipefail

cd "$(dirname "$0")/.."
source .env 2>/dev/null || true

python keymaster.py --rotate >> logs/keymaster.log 2>&1
