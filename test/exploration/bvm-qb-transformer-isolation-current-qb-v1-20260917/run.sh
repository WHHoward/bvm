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
L_PRI_PH="0.20"
L_SEC_PH="2.00"
K_ISO="0.50"
R_PRI_OHM="12.0"

SCRIPT_DIR="$OUTPUT_ROOT"
ARGS=(--josim-bin "$JOSIM_BIN" --dt "$DT" --stop-time "$STOP_TIME" --masks "${MASKS[@]}" --l-pri "$L_PRI_PH" --l-sec "$L_SEC_PH" --k-iso "$K_ISO" --r-pri "$R_PRI_OHM")

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
