#!/usr/bin/env bash
set -euo pipefail

# This reference scaffold is intentionally not a runnable scientific fixture.
# Replace TEMPLATE_PLACEHOLDER sources and empty solver values in a concrete
# series before allowing a physical run.

# ============================================================
# 1. CIRCUIT / DECK SELECTION
# ============================================================
SERIES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOP_DECK="circuits/top.cir"
BVM_CIRCUIT=""
QB_CIRCUIT=""
JTL_CIRCUIT=""
COMMON_SL_CIRCUIT=""
JSL_CIRCUIT=""

# ============================================================
# 2. STIMULUS
# ============================================================
STIMULUS_MODE="manual"       # generated or manual
MANUAL_STIMULUS="stimuli/manual.inc"
MASKS=(
    "EDIT_MASK_1"
    "EDIT_MASK_2"
)

WRITE_ENABLE=0
WRITE_START_PS=""
WRITE_RISE_PS=""
WRITE_FALL_PS=""
WRITE_WIDTH_PS=""

READ_ENABLE=0
READ_START_PS=""
READ_RISE_PS=""
READ_FALL_PS=""
READ_WIDTH_PS=""

WL_AMPLITUDE_UA=""
BL_AMPLITUDE_UA=""
SE_AMPLITUDE_UA=""

# ============================================================
# 3. EXPERIMENT PARAMETERS
# ============================================================
# Add only parameters used by this concrete series.

# ============================================================
# 4. SOLVER
# ============================================================
JOSIM_BIN=""
DT=""
STOP_TIME=""

# ============================================================
# 5. RUN BEHAVIOR
# ============================================================
RUN_ANALYSIS=1
RUN_PLOTS=1
PYTHON_BIN="python3"

usage() {
    sed -n '1,115p' "${BASH_SOURCE[0]}"
    cat <<'EOF'

Usage:
  ./run.sh --dry-run
  ./run.sh
  ./run.sh --only MASK
  ./run.sh --case CASE_ID
  ./run.sh --no-analysis
  ./run.sh --no-plots

Each non-dry invocation creates the next immutable Axxx attempt. There is no
overwrite-oriented --force option.
EOF
}

ARGS=(
    --series-dir "$SERIES_DIR"
    --top-deck "$TOP_DECK"
    --bvm-circuit "$BVM_CIRCUIT"
    --qb-circuit "$QB_CIRCUIT"
    --jtl-circuit "$JTL_CIRCUIT"
    --common-sl-circuit "$COMMON_SL_CIRCUIT"
    --jsl-circuit "$JSL_CIRCUIT"
    --stimulus-mode "$STIMULUS_MODE"
    --manual-stimulus "$MANUAL_STIMULUS"
    --masks "${MASKS[@]}"
    --write-enable "$WRITE_ENABLE"
    --write-start-ps "$WRITE_START_PS"
    --write-rise-ps "$WRITE_RISE_PS"
    --write-fall-ps "$WRITE_FALL_PS"
    --write-width-ps "$WRITE_WIDTH_PS"
    --read-enable "$READ_ENABLE"
    --read-start-ps "$READ_START_PS"
    --read-rise-ps "$READ_RISE_PS"
    --read-fall-ps "$READ_FALL_PS"
    --read-width-ps "$READ_WIDTH_PS"
    --wl-amplitude-ua "$WL_AMPLITUDE_UA"
    --bl-amplitude-ua "$BL_AMPLITUDE_UA"
    --se-amplitude-ua "$SE_AMPLITUDE_UA"
    --josim-bin "$JOSIM_BIN"
    --dt "$DT"
    --stop-time "$STOP_TIME"
)

while (($#)); do
    case "$1" in
        --help|-h)
            usage
            exit 0
            ;;
        --dry-run)
            ARGS+=(--dry-run)
            shift
            ;;
        --only)
            [[ $# -ge 2 ]] || { echo "--only requires MASK" >&2; exit 2; }
            ARGS+=(--only "$2")
            shift 2
            ;;
        --case)
            [[ $# -ge 2 ]] || { echo "--case requires CASE_ID" >&2; exit 2; }
            ARGS+=(--case "$2")
            shift 2
            ;;
        --no-analysis)
            ARGS+=(--no-analysis)
            shift
            ;;
        --no-plots)
            ARGS+=(--no-plots)
            shift
            ;;
        *)
            echo "unknown option: $1" >&2
            echo "run ./run.sh --help for usage" >&2
            exit 2
            ;;
    esac
done

(( RUN_ANALYSIS )) || ARGS+=(--no-analysis)
(( RUN_PLOTS )) || ARGS+=(--no-plots)

exec "$PYTHON_BIN" "$SERIES_DIR/scripts/build_cases.py" "${ARGS[@]}"
