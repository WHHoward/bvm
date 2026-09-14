#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  prepare) python3 analysis/prepare_closure.py ;;
  refresh-preflight) python3 analysis/prepare_closure.py --refresh-head ;;
  closure) python3 analysis/run_closure.py ;;
  qa) python3 analysis/qa_closure.py && python3 analysis/independent_closure.py ;;
  viz) python3 analysis/render_closure.py && python3 analysis/visualization_qa.py ;;
  package) python3 analysis/package_closure.py ;;
  *) echo "usage: $0 {prepare|refresh-preflight|closure|qa|viz|package}" >&2; exit 2 ;;
esac
