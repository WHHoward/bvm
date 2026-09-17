#!/usr/bin/env bash
set -euo pipefail

SERIES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="python3"

GENERATE_HTML=1
GENERATE_STATIC=0

usage() {
    cat <<'EOF'
Usage:
  ./plot.sh A001
  ./plot.sh A001 --list-signals
  ./plot.sh A001 --group QB
  ./plot.sh A001 --window 110 150
  ./plot.sh A001 --static
  ./plot.sh A001 --signals 'P(BJ1|XBQ1)' 'V(QBIN)'

This series never generates cross-run comparisons. Default output is exhaustive
standalone HTML; --window and --signals are non-destructive adhoc views.
EOF
}

ATTEMPT=""
LIST_SIGNALS=0
GROUP=""
ADHOC=0
STATIC=0
WINDOW_START=""
WINDOW_END=""
SIGNALS=()

while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --list-signals) LIST_SIGNALS=1; shift ;;
        --group)
            [[ $# -ge 2 ]] || { echo "--group requires GROUP" >&2; exit 2; }
            GROUP="$2"; shift 2 ;;
        --window)
            [[ $# -ge 3 ]] || { echo "--window requires START END" >&2; exit 2; }
            WINDOW_START="$2"; WINDOW_END="$3"; shift 3 ;;
        --static) STATIC=1; shift ;;
        --signals)
            ADHOC=1; shift
            while (($#)) && [[ "$1" != --* ]]; do SIGNALS+=("$1"); shift; done
            ((${#SIGNALS[@]} > 0)) || { echo "--signals requires exact signal names" >&2; exit 2; }
            ;;
        --*) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
        *)
            [[ -z "$ATTEMPT" ]] || { echo "unexpected argument: $1" >&2; exit 2; }
            ATTEMPT="$1"; shift ;;
    esac
done

if ((LIST_SIGNALS)); then
    [[ -n "$ATTEMPT" ]] || { echo "--list-signals requires ATTEMPT" >&2; usage >&2; exit 2; }
    exec "$PYTHON_BIN" "$SERIES_DIR/scripts/render_plots.py" --series-dir "$SERIES_DIR" --attempt "$ATTEMPT" --list-signals
fi

[[ -n "$ATTEMPT" ]] || { echo "plot.sh requires ATTEMPT" >&2; usage >&2; exit 2; }
ARGS=(--series-dir "$SERIES_DIR" --attempt "$ATTEMPT")
[[ -n "$GROUP" ]] && ARGS+=(--group "$GROUP")
[[ -n "$WINDOW_START" ]] && ARGS+=(--window "$WINDOW_START" "$WINDOW_END")
((STATIC)) && ARGS+=(--static)
if ((ADHOC)); then
    ARGS+=(--adhoc --signals "${SIGNALS[@]}")
fi

exec "$PYTHON_BIN" "$SERIES_DIR/scripts/render_plots.py" "${ARGS[@]}"
