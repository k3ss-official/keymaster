#!/usr/bin/env bash
# Validation script invoked by launchd / cron
set -euo pipefail

cd "$(dirname "$0")/.."
source .env 2>/dev/null || true

python keymaster.py --validate >> logs/keymaster-validate.log 2>&1
