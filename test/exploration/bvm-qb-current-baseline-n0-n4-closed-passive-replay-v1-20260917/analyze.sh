#!/usr/bin/env bash
set -euo pipefail

SERIES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"

if (($# == 0)); then
    echo "usage: ./analyze.sh A001" >&2
    exit 2
fi
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "usage: ./analyze.sh A001"
    echo "Reads existing raw files and writes mechanical QA/statistics only."
    exit 0
fi

exec "$PYTHON_BIN" "$SERIES_DIR/scripts/analyze.py" --series-dir "$SERIES_DIR" "$@"
