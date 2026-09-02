#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(git -C "$ROOT" rev-parse --show-toplevel)"
command="${1:-run}"
if [[ "$#" -gt 0 ]]; then
  shift
fi

case "$command" in
  run|analyze|plot|inspect) ;;
  *)
    echo "usage: ./run.sh [run|analyze|plot|inspect] [Axxx]" >&2
    exit 2
    ;;
esac

exec python3 "$REPO/scripts/bvm-exp.py" "$command" "$ROOT" "$@"
