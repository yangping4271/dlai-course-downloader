#!/usr/bin/env bash
set -euo pipefail
# Use uv to run the export script from any working directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
uv run --project "$SCRIPT_DIR" python "$SCRIPT_DIR/scripts/export_csv.py" "$@"
