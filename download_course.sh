#!/usr/bin/env bash
set -euo pipefail
# Run from any working directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
uv run --project "$SCRIPT_DIR" python "$SCRIPT_DIR/download_course.py" "$@"
