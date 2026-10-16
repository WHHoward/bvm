#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
case "${1-}" in
  --v9-multiply-batch|--resume-v9-multiply-batch|--v9-case)
    exec python3 scripts/v9_multiply_batch.py "$@"
    ;;
esac
exec python3 scripts/diagonal_platform.py "$@"
