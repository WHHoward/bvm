#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -ne 1 ]]; then
  echo "Usage: ./archive.sh <V9R###_CASE_RUN_ID>" >&2
  exit 2
fi
exec python3 "$HERE/scripts/platform.py" --archive-run "$1"
