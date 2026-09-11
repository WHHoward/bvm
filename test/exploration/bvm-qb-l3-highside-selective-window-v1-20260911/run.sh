#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  prepare) python3 analysis/prepare_l3.py ;;
  refresh-preflight) python3 analysis/prepare_l3.py --refresh-head ;;
  l3) python3 analysis/run_l3.py ;;
  qa) python3 analysis/qa_l3.py && python3 analysis/independent_l3.py ;;
  viz) python3 analysis/render_l3.py && python3 analysis/visualization_qa.py ;;
  package) python3 analysis/package_l3.py ;;
  *) echo "usage: $0 {prepare|refresh-preflight|l3|qa|viz|package}" >&2; exit 2 ;;
esac
