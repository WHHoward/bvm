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
  python3 "$PLOTTER" raw.csv -t stacked -c dark -j 2pi -x bvm_res.html \
  -s \
  "V(SJTL_OUT_D0_L1)" "V(SJTL_OUT_D1_L2)" "V(SJTL_OUT_D2_L3)" "V(SJTL_OUT_D3_L4)" \
  "V(SJTL_OUT_D4_L3)" "V(SJTL_OUT_D5_L2)" "V(SJTL_OUT_D6_L1)"

  python3 "$PLOTTER" raw.csv -t stacked -c dark -j 2pi -x t1_in.html \
  -s \
  "V(T1_I_D0)" "V(T1_I_D1)" "V(T1_I_D2)" "V(T1_I_D3)" \
  "V(T1_I_D4)" "V(T1_I_D5)" "V(T1_I_D6)" "V(DFF_IN)" "V(CLK_D5)"

  python3 "$PLOTTER" raw.csv -t stacked -c dark -j 2pi -x carry.html \
  -s \
  "V(C_D0)" "V(C_D1)" "V(C_D2)" "V(C_D3)" \
  "V(C_D4)" "V(C_D5)" "V(DFF_IN)" 

  python3 "$PLOTTER" raw.csv -t stacked -c dark -j 2pi -x t1_merge.html \
  -s \
  "V(CARRY_CB_IN_D1)" "V(CARRY_CB_IN_D2)" "V(CARRY_CB_IN_D3)" \
  "V(CARRY_CB_IN_D4)" "V(CARRY_CB_IN_D5)" "V(CARRY_CB_IN_D6)" 

  python3 "$PLOTTER" raw.csv -t stacked -c dark -j 2pi -x bvm_current.html \
  -s \
  "I(R_SE|XBVM_R1C1)"\
  "I(R_SE|XBVM_R1C2)"\
  "I(R_SE|XBVM_R1C3)"\
  "I(R_SE|XBVM_R1C4)"     
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
