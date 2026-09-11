#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  prepare) python3 analysis/prepare_combination.py ;;
  refresh-preflight) python3 analysis/prepare_combination.py --refresh-head ;;
  combine) python3 analysis/run_combination.py ;;
  validate) python3 analysis/run_candidate_validation.py ;;
  qa) python3 analysis/qa_combination.py && python3 analysis/independent_combination.py ;;
  viz) python3 analysis/render_combination.py && python3 analysis/visualization_qa.py ;;
  package) python3 analysis/package_combination.py ;;
  *) echo "usage: $0 {prepare|refresh-preflight|combine|validate|qa|viz|package}" >&2; exit 2 ;;
esac
