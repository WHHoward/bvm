#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# 1. CIRCUIT / DECK SELECTION
# ============================================================
SERIES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOSED_TOP_DECK="circuits/closed_top.cir"
PASSIVE_TOP_DECK="circuits/passive_top.cir"
REPLAY_TOP_DECK="circuits/replay_top.cir"

# Current canonical sources; the builder snapshots them into each attempt.
JJ_MODEL="../../../circuits/models/jjmit.cir"
BVM_CIRCUIT="../../../test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/bvm_jm2_connected.cir"
QB_CIRCUIT="../../../circuits/qb/bq_parameterized_v1.cir"
JTL_CIRCUIT="../../../test/exploration/bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914/inputs/jtl2.cir"

# ============================================================
# 2. STIMULUS
# ============================================================
STIMULUS_MODE="generated"
MANUAL_STIMULUS=""
MASKS=(0000 0001 0011 0111 1111)
BIT_ORDER="b3b2b1b0=BVM1/BVM2/BVM3/BVM4"

WRITE0_START_PS="50"
WRITE0_RISE_PS="1"
WRITE0_FALL_PS="1"
WRITE0_WIDTH_PS="9"
ZERO_READ_START_PS="70"
ZERO_READ_RISE_PS="1"
ZERO_READ_FALL_PS="1"
ZERO_READ_WIDTH_PS="9"
WRITE1_START_PS="90"
WRITE1_RISE_PS="1"
WRITE1_FALL_PS="1"
WRITE1_WIDTH_PS="9"
FINAL_READ_START_PS="110"
FINAL_READ_RISE_PS="1"
FINAL_READ_FALL_PS="1"
FINAL_READ_WIDTH_PS="9"
WL_AMPLITUDE_UA="100"
BL_AMPLITUDE_UA="100"
SE_AMPLITUDE_UA="100"

# ============================================================
# 3. EXPERIMENT PARAMETERS
# ============================================================
TERMINAL_OHM="10"
JSL_AREA="5.0"
REPLAY_SOURCE_SIGNAL="I(B_JSL8)"

# ============================================================
# 4. SOLVER
# ============================================================
JOSIM_BIN="../../../build/josim-cli"
DT="0.1p"
STOP_TIME="200p"

# ============================================================
# 5. RUN BEHAVIOR
# ============================================================
RUN_ANALYSIS=1
RUN_PLOTS=1
PYTHON_BIN="python3"

usage() {
    cat <<'EOF'
Usage:
  ./run.sh --dry-run
  ./run.sh
  ./run.sh --only 0111       # inspection only for this fixed baseline
  ./run.sh --case CLOSED_N3_0111  # inspection only
  ./run.sh --no-analysis
  ./run.sh --no-plots

The physical baseline always requires the registered 15-case default matrix.
Every invocation creates a new immutable Axxx attempt; no overwrite option is
provided.
EOF
}

ARGS=(
    --series-dir "$SERIES_DIR"
    --closed-top-deck "$CLOSED_TOP_DECK"
    --passive-top-deck "$PASSIVE_TOP_DECK"
    --replay-top-deck "$REPLAY_TOP_DECK"
    --jj-model "$JJ_MODEL"
    --bvm-circuit "$BVM_CIRCUIT"
    --qb-circuit "$QB_CIRCUIT"
    --jtl-circuit "$JTL_CIRCUIT"
    --stimulus-mode "$STIMULUS_MODE"
    --manual-stimulus "$MANUAL_STIMULUS"
    --masks "${MASKS[@]}"
    --bit-order "$BIT_ORDER"
    --write0-start-ps "$WRITE0_START_PS"
    --write0-rise-ps "$WRITE0_RISE_PS"
    --write0-fall-ps "$WRITE0_FALL_PS"
    --write0-width-ps "$WRITE0_WIDTH_PS"
    --zero-read-start-ps "$ZERO_READ_START_PS"
    --zero-read-rise-ps "$ZERO_READ_RISE_PS"
    --zero-read-fall-ps "$ZERO_READ_FALL_PS"
    --zero-read-width-ps "$ZERO_READ_WIDTH_PS"
    --write1-start-ps "$WRITE1_START_PS"
    --write1-rise-ps "$WRITE1_RISE_PS"
    --write1-fall-ps "$WRITE1_FALL_PS"
    --write1-width-ps "$WRITE1_WIDTH_PS"
    --final-read-start-ps "$FINAL_READ_START_PS"
    --final-read-rise-ps "$FINAL_READ_RISE_PS"
    --final-read-fall-ps "$FINAL_READ_FALL_PS"
    --final-read-width-ps "$FINAL_READ_WIDTH_PS"
    --wl-amplitude-ua "$WL_AMPLITUDE_UA"
    --bl-amplitude-ua "$BL_AMPLITUDE_UA"
    --se-amplitude-ua "$SE_AMPLITUDE_UA"
    --terminal-ohm "$TERMINAL_OHM"
    --jsl-area "$JSL_AREA"
    --replay-source-signal "$REPLAY_SOURCE_SIGNAL"
    --josim-bin "$JOSIM_BIN"
    --dt "$DT"
    --stop-time "$STOP_TIME"
)

while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --dry-run) ARGS+=(--dry-run); shift ;;
        --only)
            [[ $# -ge 2 ]] || { echo "--only requires MASK" >&2; exit 2; }
            ARGS+=(--only "$2"); shift 2 ;;
        --case)
            [[ $# -ge 2 ]] || { echo "--case requires CASE_ID" >&2; exit 2; }
            ARGS+=(--case "$2"); shift 2 ;;
        --no-analysis) ARGS+=(--no-analysis); shift ;;
        --no-plots) ARGS+=(--no-plots); shift ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

(( RUN_ANALYSIS )) || ARGS+=(--no-analysis)
(( RUN_PLOTS )) || ARGS+=(--no-plots)

exec "$PYTHON_BIN" "$SERIES_DIR/scripts/build_cases.py" "${ARGS[@]}"
