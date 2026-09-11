#!/usr/bin/env bash
set -euo pipefail

case "${1:-}" in
  prepare)
    python3 analysis/prepare_mechanism.py
    ;;
  refresh-preflight)
    python3 analysis/prepare_mechanism.py --refresh-head
    ;;
  passive)
    python3 analysis/run_passive.py
    ;;
  build-replay)
    python3 analysis/build_replay.py
    ;;
  replay-preflight)
    python3 analysis/replay_preflight.py
    ;;
  replay)
    python3 analysis/run_replay.py
    ;;
  qa)
    python3 analysis/raw_mechanism_analysis.py
    python3 analysis/qa_mechanism.py
    python3 analysis/independent_mechanism_review.py
    ;;
  viz)
    python3 analysis/render_mechanism_plots.py
    python3 analysis/visualization_qa.py
    ;;
  package)
    python3 analysis/package_mechanism.py
    ;;
  *)
    echo "usage: $0 {prepare|refresh-preflight|passive|build-replay|replay-preflight|replay|qa|viz|package}" >&2
    exit 2
    ;;
esac
