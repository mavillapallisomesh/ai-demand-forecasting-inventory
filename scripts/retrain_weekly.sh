#!/usr/bin/env bash
# Weekly retraining job — re-runs the whole pipeline (ingest -> DQ -> train ->
# inventory -> dashboard) and appends a timestamped log line.
# Install with cron (see docs/scheduling.md):
#   0 2 * * 0 /path/to/repo/scripts/retrain_weekly.sh >> /path/to/repo/outputs/retrain.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

VENV=".venv/bin/python"
if [ ! -x "$VENV" ]; then
  echo "ERROR: virtualenv not found. Run: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

echo "=== weekly retrain started $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
"$VENV" -m src.run_pipeline
echo "=== weekly retrain finished $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
