#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  prepare) python3 analysis/prepare_target.py ;;
  refresh-preflight) python3 analysis/prepare_target.py --refresh-head ;;
  target) python3 analysis/run_target.py ;;
  qa) python3 analysis/qa_target.py && python3 analysis/independent_target.py ;;
  viz) python3 analysis/render_target.py && python3 analysis/visualization_qa.py ;;
  package) python3 analysis/package_target.py ;;
  *) echo "usage: $0 {prepare|refresh-preflight|target|qa|viz|package}" >&2; exit 2 ;;
esac
