#!/usr/bin/env bash
set -euo pipefail

SERIES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"

# ============================================================
# USER-EDITABLE PLOT SIGNALS
# ============================================================
# Fill these from a real attempt with: ./plot.sh A001 --list-signals
SIGNAL_PATH_SIGNALS=()
BVM_STATE_SIGNALS=()
BVM_OUTPUT_SIGNALS=()
JSL_CHAIN_SIGNALS=()
QB_STATE_SIGNALS=()
JTL_CHAIN_SIGNALS=()

# Default visualization contract: local interactive HTML only.
GENERATE_HTML=1
GENERATE_STATIC=0

usage() {
    cat <<'EOF'
Usage:
  ./plot.sh A001
  ./plot.sh A001 --list-signals
  ./plot.sh A001 --group QB_STATE
  ./plot.sh A001 --signals 'I(L_S3|XBVM2)' 'V(QBIN)'
  ./plot.sh A001 --window 110 121
  ./plot.sh --raw /path/to/raw.csv --list-signals
  ./plot.sh --help

Default output is offline interactive HTML through scripts/josim-plot2.py.
Ad hoc --signals output is written below runs/<attempt>/plots/<case>/adhoc/.
EOF
}

ATTEMPT=""
GROUP=""
RAW_PATH=""
LIST_SIGNALS=0
ADHOC=0
STATIC=0
WINDOW_START=""
WINDOW_END=""
ADHOC_SIGNALS=()

while (($#)); do
    case "$1" in
        --help|-h)
            usage
            exit 0
            ;;
        --list-signals)
            LIST_SIGNALS=1
            shift
            ;;
        --raw)
            [[ $# -ge 2 ]] || { echo "--raw requires a CSV path" >&2; exit 2; }
            RAW_PATH="$2"
            shift 2
            ;;
        --group)
            [[ $# -ge 2 ]] || { echo "--group requires a group name" >&2; exit 2; }
            GROUP="$2"
            shift 2
            ;;
        --window)
            [[ $# -ge 3 ]] || { echo "--window requires START END in ps" >&2; exit 2; }
            WINDOW_START="$2"
            WINDOW_END="$3"
            shift 3
            ;;
        --static)
            STATIC=1
            shift
            ;;
        --signals)
            ADHOC=1
            shift
            while (($#)) && [[ "$1" != --* ]]; do
                ADHOC_SIGNALS+=("$1")
                shift
            done
            ((${#ADHOC_SIGNALS[@]} > 0)) || { echo "--signals requires at least one exact signal" >&2; exit 2; }
            ;;
        --*)
            echo "unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
        *)
            [[ -z "$ATTEMPT" ]] || { echo "unexpected argument: $1" >&2; exit 2; }
            ATTEMPT="$1"
            shift
            ;;
    esac
done

if ((LIST_SIGNALS)); then
    ARGS=(--series-dir "$SERIES_DIR" --list-signals)
    [[ -n "$ATTEMPT" ]] && ARGS+=(--attempt "$ATTEMPT")
    [[ -n "$RAW_PATH" ]] && ARGS+=(--raw "$RAW_PATH")
    exec "$PYTHON_BIN" "$SERIES_DIR/scripts/render_plots.py" "${ARGS[@]}"
fi

[[ -n "$ATTEMPT" ]] || { echo "plot.sh requires an attempt such as A001" >&2; usage >&2; exit 2; }
[[ -z "$RAW_PATH" ]] || { echo "--raw is only valid with --list-signals" >&2; exit 2; }

COMMON_ARGS=(--series-dir "$SERIES_DIR" --attempt "$ATTEMPT")
if [[ -n "$WINDOW_START" ]]; then
    COMMON_ARGS+=(--window "$WINDOW_START" "$WINDOW_END")
fi
if ((STATIC)); then
    GENERATE_STATIC=1
    COMMON_ARGS+=(--static)
fi

if ((ADHOC)); then
    exec "$PYTHON_BIN" "$SERIES_DIR/scripts/render_plots.py" "${COMMON_ARGS[@]}" --adhoc --signals "${ADHOC_SIGNALS[@]}"
fi

render_group() {
    local group="$1"
    shift
    (($# > 0)) || { echo "group $group has no configured signals; edit plot.sh or run --list-signals" >&2; exit 2; }
    "$PYTHON_BIN" "$SERIES_DIR/scripts/render_plots.py" "${COMMON_ARGS[@]}" --group "$group" --signals "$@"
}

if [[ -n "$GROUP" ]]; then
    case "$GROUP" in
        SIGNAL_PATH) render_group SIGNAL_PATH "${SIGNAL_PATH_SIGNALS[@]}" ;;
        BVM_STATE) render_group BVM_STATE "${BVM_STATE_SIGNALS[@]}" ;;
        BVM_OUTPUT) render_group BVM_OUTPUT "${BVM_OUTPUT_SIGNALS[@]}" ;;
        JSL_CHAIN) render_group JSL_CHAIN "${JSL_CHAIN_SIGNALS[@]}" ;;
        QB_STATE) render_group QB_STATE "${QB_STATE_SIGNALS[@]}" ;;
        JTL_CHAIN) render_group JTL_CHAIN "${JTL_CHAIN_SIGNALS[@]}" ;;
        *) echo "unknown group: $GROUP" >&2; exit 2 ;;
    esac
    exit 0
fi

render_group SIGNAL_PATH "${SIGNAL_PATH_SIGNALS[@]}"
render_group BVM_STATE "${BVM_STATE_SIGNALS[@]}"
render_group BVM_OUTPUT "${BVM_OUTPUT_SIGNALS[@]}"
render_group JSL_CHAIN "${JSL_CHAIN_SIGNALS[@]}"
render_group QB_STATE "${QB_STATE_SIGNALS[@]}"
render_group JTL_CHAIN "${JTL_CHAIN_SIGNALS[@]}"
