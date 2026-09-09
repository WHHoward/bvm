#!/usr/bin/env bash
set -euo pipefail

EXP_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

case "${1:-help}" in
  prepare)
    exec python3 "$EXP_DIR/analysis/prepare_experiment.py"
    ;;
  refresh-preflight)
    exec python3 "$EXP_DIR/analysis/prepare_experiment.py" --refresh-head
    ;;
  run)
    exec python3 "$EXP_DIR/analysis/execute_runs.py"
    ;;
  qa)
    exec python3 "$EXP_DIR/analysis/qa_pipeline.py"
    ;;
  viz-standalone)
    exec python3 "$EXP_DIR/analysis/render_v2_1.py" v2_1_standalone
    ;;
  viz-comparison)
    exec python3 "$EXP_DIR/analysis/render_v2_1.py" v2_1_comparison
    ;;
  viz-qa)
    exec python3 "$EXP_DIR/analysis/visualization_qa.py"
    ;;
  package)
    exec python3 "$EXP_DIR/analysis/package_experiment.py"
    ;;
  help|*)
    echo "usage: $0 {prepare|refresh-preflight|run|qa|viz-standalone|viz-comparison|viz-qa|package}"
    exit 2
    ;;
esac
