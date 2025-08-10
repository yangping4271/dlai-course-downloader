#!/usr/bin/env bash
set -euo pipefail
uv run python download_course.py "$@"
