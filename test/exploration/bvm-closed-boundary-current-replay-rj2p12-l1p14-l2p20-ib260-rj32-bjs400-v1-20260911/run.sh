#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  prepare) python3 analysis/prepare_stage_a.py ;;
  refresh-preflight) python3 analysis/prepare_stage_a.py --refresh-head ;;
  stage-a) python3 analysis/run_stage_a.py ;;
  analyze) python3 analysis/analyze_stage_a.py ;;
  qa) python3 analysis/qa_stage_a.py && python3 analysis/independent_stage_a.py ;;
  viz) python3 analysis/render_stage_a.py && python3 analysis/visualization_qa.py ;;
  package) python3 analysis/package_stage_a.py ;;
  *) echo "usage: $0 {prepare|refresh-preflight|stage-a|analyze|qa|viz|package}" >&2; exit 2 ;;
esac
