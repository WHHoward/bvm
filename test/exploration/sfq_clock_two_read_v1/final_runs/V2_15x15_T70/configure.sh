#!/usr/bin/env bash
# Simple local front-end for the frozen BVM stimulus generator.
# From final_runs/: prepare a new named case in a fresh child directory.
# From a child case: update the generated stimulus/deck BEFORE any solver run.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$HERE" rev-parse --show-toplevel)" || {
  echo 'ERROR: this script must be inside the WHHoward/bvm Git checkout.' >&2
  exit 2
}
BASE="$REPO_ROOT/test/exploration/sfq_clock_two_read_v1/final_runs"
GENERATOR="$REPO_ROOT/scripts/bvm_stimulus.py"
ORIGINAL_DECK="$REPO_ROOT/test/exploration/sfq_clock_two_read_v1/sfq_clock_timesteptest/deck.cir"
RUNNER_TEMPLATE="$BASE/V0_15x15_T70/run.sh"
CONFIG="$HERE/USER_CASE.env"

fail() { echo "ERROR: $*" >&2; exit 2; }
usage() {
  cat <<'HELP'
Usage: ./configure.sh [--dry-run]
  In final_runs/: create a fresh named experiment directory from USER_CASE.env.
  In a generated experiment directory: regenerate stimulus and .tran before any run.
  Never runs JoSIM. Never overwrites an existing raw/log.
HELP
}
[[ $# -le 1 ]] || fail 'too many arguments; use --help or --dry-run'
ACTION="${1:-prepare}"
case "$ACTION" in prepare|--dry-run|--help) ;; *) usage; exit 2 ;; esac
if [[ "$ACTION" == '--help' ]]; then usage; exit 0; fi
[[ -f "$CONFIG" ]] || fail "missing config file: $CONFIG"
[[ -f "$GENERATOR" ]] || fail "missing existing generator: $GENERATOR"
# shellcheck disable=SC1090
source "$CONFIG"
: "${A:?set operand A in USER_CASE.env}"
: "${B:?set operand B in USER_CASE.env}"
: "${ROUNDS:?set ROUNDS in USER_CASE.env}"
: "${READ_INTERVAL_PS:?set READ_INTERVAL_PS in USER_CASE.env}"
: "${WRITE_START_PS:?set WRITE_START_PS in USER_CASE.env}"
: "${FIRST_READ_PS:?set FIRST_READ_PS in USER_CASE.env}"
: "${DT_PS:?set DT_PS in USER_CASE.env}"
: "${TAIL_PS:?set TAIL_PS in USER_CASE.env}"
PROBES="${PROBES:-outputs}"
[[ "$PROBES" == 'outputs' || "$PROBES" == 'outputs-clocks' ]] || fail 'PROBES must be outputs or outputs-clocks'

args=(--a "$A" --b "$B" --read-interval-ps "$READ_INTERVAL_PS"
      --rounds "$ROUNDS" --write-start-ps "$WRITE_START_PS"
      --first-read-ps "$FIRST_READ_PS" --dt-ps "$DT_PS"
      --tail-ps "$TAIL_PS")
[[ -z "${CLOCK_PERIOD_PS:-}" ]] || args+=(--clock-period-ps "$CLOCK_PERIOD_PS")
[[ -z "${SE_CLOCK_DELAY_PS:-}" ]] || args+=(--se-clock-delay-ps "$SE_CLOCK_DELAY_PS")
[[ -z "${STOP_PS:-}" ]] || args+=(--stop-ps "$STOP_PS")

if [[ "$HERE" == "$BASE" ]]; then
  [[ -f "$ORIGINAL_DECK" ]] || fail "source deck missing: $ORIGINAL_DECK"
  [[ -f "$RUNNER_TEMPLATE" ]] || fail "simple run.sh missing: $RUNNER_TEMPLATE"
  : "${CASE_NAME:?set a unique CASE_NAME in USER_CASE.env}"
  [[ "$CASE_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || fail 'CASE_NAME may contain only letters, digits, _ and -'
  DEST="$BASE/$CASE_NAME"
  [[ ! -e "$DEST" ]] || fail "case already exists: $DEST. Choose a NEW CASE_NAME; prior runs must not be overwritten"
  echo "NEW CASE: $DEST"
  echo "A=$A, B=$B, rounds=$ROUNDS; read T=${READ_INTERVAL_PS}ps; clock T=${CLOCK_PERIOD_PS:-$READ_INTERVAL_PS}ps; SE->clock=${SE_CLOCK_DELAY_PS:-$READ_INTERVAL_PS}ps"
  if [[ "$ACTION" == '--dry-run' ]]; then
    echo 'DRY RUN: no files created.'
    exit 0
  fi
  python3 "$GENERATOR" init --template "$ORIGINAL_DECK" --dir "$DEST" --probes "$PROBES"
  cp "$HERE/configure.sh" "$HERE/USER_CASE.env" "$DEST/"
  cp "$RUNNER_TEMPLATE" "$DEST/run.sh"
  chmod +x "$DEST/run.sh" "$DEST/configure.sh"
  python3 "$GENERATOR" set --dir "$DEST" "${args[@]}"
  echo
  echo "PREPARED: $DEST"
  echo "Next: cd '$DEST' && ./run.sh   (or ./run.sh --html)"
elif [[ "$HERE" == "$BASE/"* ]]; then
  [[ -f "$HERE/deck.template.cir" && -f "$HERE/SOURCE_MANIFEST.json" ]] || fail 'not an initialized, frozen case directory'
  for artifact in raw.csv data_tran.csv run.log res.html; do
    [[ ! -e "$HERE/$artifact" ]] || fail "existing $artifact found. Create a NEW CASE_NAME under $BASE; no in-place changes after a run"
  done
  echo "UPDATING UNSOLVED CASE: $HERE"
  if [[ "$ACTION" == '--dry-run' ]]; then
    echo 'DRY RUN: no files changed.'
    exit 0
  fi
  python3 "$GENERATOR" set --dir "$HERE" "${args[@]}" --overwrite
  echo 'Generated stimulus.inc and updated .tran; source circuits unchanged.'
else
  fail "place configure.sh in $BASE or a generated direct child case directory"
fi
