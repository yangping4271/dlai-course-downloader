#!/usr/bin/env bash
set -euo pipefail
# Use uv to run the export script
uv run python scripts/export_csv.py ""
