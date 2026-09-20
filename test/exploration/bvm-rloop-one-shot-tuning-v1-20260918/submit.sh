#!/usr/bin/env bash
set -euo pipefail
SERIES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SERIES_DIR/scripts/submit.py" "$@"

