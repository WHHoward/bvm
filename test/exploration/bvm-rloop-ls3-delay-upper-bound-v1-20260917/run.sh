#!/usr/bin/env bash
set -euo pipefail

# USER-EDITABLE PARAMETERS
JOSIM_BIN="/home/howard/JoSIM/build/josim-cli"
DT="0.1p"
STOP_TIME="200p"
MASKS=(0011 0111)
OUTPUT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORCE=0
RUN_ANALYSIS=1
RUN_PLOTS=1
DRY_RUN=0
DELAYS_PS=("0.5")

SCRIPT_DIR="$OUTPUT_ROOT"
ARGS=(--josim-bin "$JOSIM_BIN" --dt "$DT" --stop-time "$STOP_TIME" --masks "${MASKS[@]}" --delays "${DELAYS_PS[@]}")

while (($#)); do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --force) FORCE=1; shift ;;
    --only) ARGS+=(--only "$2"); shift 2 ;;
    --no-analysis) RUN_ANALYSIS=0; shift ;;
    --no-plots) RUN_PLOTS=0; shift ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

(( FORCE )) && ARGS+=(--force)
(( RUN_ANALYSIS )) || ARGS+=(--no-analysis)
(( RUN_PLOTS )) || ARGS+=(--no-plots)
(( DRY_RUN )) && ARGS+=(--dry-run)

exec python3 "$SCRIPT_DIR/generator.py" "${ARGS[@]}"
