#!/usr/bin/env bash
set -euo pipefail

experiment_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-help}" in
  preflight)
    exec python3 "$experiment_dir/analysis/preflight.py"
    ;;
  run)
    exec python3 "$experiment_dir/analysis/execute_runs.py"
    ;;
  qa)
    exec python3 "$experiment_dir/analysis/raw_qa.py"
    ;;
  analyze)
    exec python3 "$experiment_dir/analysis/analyze.py"
    ;;
  plot-standalone)
    exec python3 "$experiment_dir/analysis/render_plots.py" standalone
    ;;
  plot-comparison)
    exec python3 "$experiment_dir/analysis/render_plots.py" comparison
    ;;
  viz-qa)
    exec python3 "$experiment_dir/analysis/visualization_qa.py"
    ;;
  help|*)
    echo "usage: $0 {preflight|run|qa|analyze|plot-standalone|plot-comparison|viz-qa}"
    exit 2
    ;;
esac
