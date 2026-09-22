#!/usr/bin/env bash
# Rotation script invoked by launchd / cron on Janet's MBP
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs

set -a
# shellcheck disable=SC1091
[[ -f .env ]] && source .env
set +a

exec python3 keymaster.py --rotate >> logs/keymaster.log 2>&1
