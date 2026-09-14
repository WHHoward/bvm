#!/usr/bin/env bash
set -euo pipefail

EXP_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$EXP_ROOT/../../.." && pwd)"
export BVM_QB_T1_EXPERIMENT_ID="bvm-qb-t1-interface-topology-v1-20260914-bias-1p8-rj4-4-rerun"
export BVM_QB_T1_OLD_EXP_ID="bvm-qb-t1-interface-topology-v1-20260914-bias-1p8-rerun"
export BVM_QB_T1_RJ4_BEFORE=2
export BVM_QB_T1_RJ4_AFTER=4
export BVM_QB_T1_DECK_SOURCE="$EXP_ROOT/runs/jtl6/0011/deck.cir"
RUNNER="$REPO_ROOT/scripts/bvm_qb_t1_single_rerun.py"
RAW="$EXP_ROOT/runs/jtl6/0011/raw.csv"
LOG="$EXP_ROOT/runs/jtl6/0011/run.log"

command="${1:-run}"

prepare() {
  if [[ -e "$RAW" || -e "$LOG" ]]; then
    echo "refusing prepare: raw.csv or run.log already exists; create a new run ID" >&2
    exit 3
  fi
  python3 "$RUNNER" prepare
}

case "$command" in
  prepare) prepare ;;
  run)
    [[ -f "$EXP_ROOT/run_state.json" ]] || prepare
    python3 "$RUNNER" run
    ;;
  qa) python3 "$RUNNER" qa ;;
  viz) python3 "$RUNNER" viz ;;
  package) python3 "$RUNNER" package ;;
  all)
    prepare
    python3 "$RUNNER" run
    python3 "$RUNNER" qa
    python3 "$RUNNER" viz
    python3 "$RUNNER" package
    ;;
  *)
    echo "usage: $0 {prepare|run|qa|viz|package|all}" >&2
    exit 2
    ;;
esac
