#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  prepare) python3 analysis/prepare_boundary.py ;;
  refresh-preflight) python3 analysis/prepare_boundary.py --refresh-head ;;
  boundary) python3 analysis/run_boundary.py ;;
  qa) python3 analysis/qa_boundary.py && python3 analysis/independent_boundary.py ;;
  viz) python3 analysis/render_boundary.py && python3 analysis/visualization_qa.py ;;
  package) python3 analysis/package_boundary.py ;;
  *) echo "usage: $0 {prepare|refresh-preflight|boundary|qa|viz|package}" >&2; exit 2 ;;
esac
