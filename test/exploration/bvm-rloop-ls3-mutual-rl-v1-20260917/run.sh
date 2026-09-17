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
M_VALUES_PH=("0.00" "0.25" "0.50" "0.75")
L_AUX_PH="10.0"
R_AUX_OHM="20.0"

SCRIPT_DIR="$OUTPUT_ROOT"
ARGS=(--josim-bin "$JOSIM_BIN" --dt "$DT" --stop-time "$STOP_TIME" --masks "${MASKS[@]}" --m-values "${M_VALUES_PH[@]}" --l-aux "$L_AUX_PH" --r-aux "$R_AUX_OHM")

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
