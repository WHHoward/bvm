#!/usr/bin/env bash
set -euo pipefail

EXP_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$EXP_ROOT/../../.." && pwd)"
export BVM_QB_T1_EXPERIMENT_ID="bvm-qb-t1-interface-topology-v1-20260914-bias-1p8-rj4-4-masks-0111-1111-rerun"
export BVM_QB_T1_TEMPLATE_DECK="$REPO_ROOT/test/exploration/bvm-qb-t1-interface-topology-v1-20260914-bias-1p8-rj4-4-rerun/runs/jtl6/0011/deck.cir"
RUNNER="$REPO_ROOT/scripts/bvm_qb_t1_mask_pair_rerun.py"

command="${1:-run}"

ensure_fresh() {
  for mask in 0111 1111; do
    raw="$EXP_ROOT/runs/jtl6/$mask/raw.csv"
    log="$EXP_ROOT/runs/jtl6/$mask/run.log"
    if [[ -e "$raw" || -e "$log" ]]; then
      echo "refusing to overwrite existing artifacts for mask $mask; create a new run ID" >&2
      exit 3
    fi
  done
}

case "$command" in
  prepare) ensure_fresh; python3 "$RUNNER" prepare ;;
  run)
    if [[ ! -f "$EXP_ROOT/run_state.json" ]]; then
      ensure_fresh
      python3 "$RUNNER" prepare
    fi
    python3 "$RUNNER" run
    ;;
  qa) python3 "$RUNNER" qa ;;
  viz) python3 "$RUNNER" viz ;;
  package) python3 "$RUNNER" package ;;
  all)
    ensure_fresh
    python3 "$RUNNER" prepare
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
