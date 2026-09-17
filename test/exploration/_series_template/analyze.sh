#!/usr/bin/env bash
set -euo pipefail

SERIES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"

usage() {
    cat <<'EOF'
Usage:
  ./analyze.sh A001
  ./analyze.sh latest
  ./analyze.sh --help

Analysis reads existing raw files only and writes mechanical summaries under
runs/<attempt>/analysis/.
EOF
}

if (($# == 0)); then
    echo "analyze.sh requires an attempt such as A001 or latest" >&2
    usage >&2
    exit 2
fi
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    usage
    exit 0
fi

exec "$PYTHON_BIN" "$SERIES_DIR/scripts/analyze.py" --series-dir "$SERIES_DIR" "$@"
