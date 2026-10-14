#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$RUN_DIR/../../../../.." && pwd)"
PLOTTER="$REPO_ROOT/scripts/josim-plot2.py"
ACTION="${1:-run}"

usage() {
  echo "Usage: ./run.sh [--html|--html-only]" >&2
  exit 2
}

[[ $# -le 1 ]] || usage
case "$ACTION" in
  run|--html|--html-only) ;;
  *) usage ;;
esac

cd "$RUN_DIR"

make_html() {
  [[ -s raw.csv ]] || { echo "ERROR: raw.csv not found; no solve performed." >&2; exit 2; }
  python3 "$PLOTTER" raw.csv -t stacked -c dark -j 2pi -x res.html \
    -s "V(S_D0_OUT)" "V(S_D1_OUT)" "V(S_D2_OUT)" "V(S_D3_OUT)" \
       "V(S_D4_OUT)" "V(S_D5_OUT)" "V(S_D6_OUT)" "V(DFF_O)"
}

if [[ "$ACTION" == "--html-only" ]]; then
  make_html
  exit 0
fi

if [[ -e raw.csv || -e run.log ]]; then
  echo "ERROR: raw.csv or run.log already exists; create a new run directory to solve again." >&2
  exit 2
fi
[[ -f deck.cir ]] || { echo "ERROR: deck.cir not found." >&2; exit 2; }
[[ -f stimulus.inc ]] || { echo "ERROR: stimulus.inc not found." >&2; exit 2; }

if [[ -n "${JOSIM_CLI:-}" ]]; then
  JOSIM="$JOSIM_CLI"
elif command -v josim-cli >/dev/null 2>&1; then
  JOSIM="$(command -v josim-cli)"
elif [[ -x "$REPO_ROOT/build/josim-cli" ]]; then
  JOSIM="$REPO_ROOT/build/josim-cli"
else
  echo "ERROR: josim-cli not found; set JOSIM_CLI or build $REPO_ROOT/build/josim-cli." >&2
  exit 2
fi
[[ -x "$JOSIM" ]] || { echo "ERROR: josim-cli is not executable: $JOSIM" >&2; exit 2; }

{
  printf 'Run directory: %s\n' "$RUN_DIR"
  printf 'Command: %s -o raw.csv deck.cir\n' "$JOSIM"
  "$JOSIM" -o raw.csv deck.cir
} 2>&1 | tee run.log

if [[ "$ACTION" == "--html" ]]; then
  make_html
fi
