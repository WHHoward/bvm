#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  prepare) python3 analysis/prepare_screening.py ;;
  refresh-preflight) python3 analysis/prepare_screening.py --refresh-head ;;
  screen) python3 analysis/run_screening.py ;;
  validate) python3 analysis/run_candidate_validation.py ;;
  qa) python3 analysis/screening_analysis.py && python3 analysis/qa_screening.py && python3 analysis/independent_screening.py ;;
  viz) python3 analysis/render_screening.py && python3 analysis/visualization_qa.py ;;
  package) python3 analysis/package_screening.py ;;
  *) echo "usage: $0 {prepare|refresh-preflight|screen|validate|qa|viz|package}" >&2; exit 2 ;;
esac
