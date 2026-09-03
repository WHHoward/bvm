#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
EXP_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(cd "$EXP_DIR/../../.." && pwd)
SOLVER="$REPO_ROOT/build/josim-cli"

[[ -x "$SOLVER" ]] || { echo "solver not executable: $SOLVER" >&2; exit 1; }
[[ -z "$(git -C "$REPO_ROOT" status --porcelain)" ]] || {
  echo "working tree is not clean; commit rerun setup before execution" >&2
  git -C "$REPO_ROOT" status --short >&2
  exit 1
}

python3 "$SCRIPT_DIR/create_jtl_probe_reruns.py"

conditions=(
  'S0-J-CORRECTED-RERUN|jtl'
  'S1-J-CORRECTED-RERUN|jtl'
)

for item in "${conditions[@]}"; do
  condition=${item%%|*}
  load=${item##*|}
  input="$EXP_DIR/inputs/$condition.cir"
  run_dir="$EXP_DIR/runs/$condition"
  raw="$run_dir/raw/run-01.csv"
  log="$run_dir/logs/run-01.log"

  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$run_dir" ]] || { echo "refusing to overwrite: $run_dir" >&2; exit 1; }
  mkdir -p "$run_dir/raw" "$run_dir/logs"
  cp -- "$input" "$run_dir/deck.cir"
  cmp -- "$input" "$run_dir/deck.cir"
  solver_hash=$(sha256sum "$SOLVER" | awk '{print $1}')
  {
    printf 'condition=%s\nload=%s\ninput=%s\ndeck=%s\nraw=%s\n' \
      "$condition" "$load" "$input" "$run_dir/deck.cir" "$raw"
    printf 'solver=%s\nsolver_sha256=%s\n' "$SOLVER" "$solver_hash"
    printf 'change=JTL P/V print observables only; no circuit physics/topology change\n'
    printf 'command=%s -a 1 -o %s %s\n' "$SOLVER" "$raw" "$input"
  } > "$run_dir/command.txt"

  set +e
  "$SOLVER" -a 1 -o "$raw" "$input" > "$log" 2>&1
  code=$?
  set -e
  printf 'exit_code=%s\n' "$code" >> "$run_dir/command.txt"
  sha256sum "$run_dir/deck.cir" "$raw" > "$run_dir/hashes.sha256" 2>/dev/null || true
  if [[ "$code" -ne 0 ]]; then
    echo "JoSIM failed for $condition; raw/log preserved at $run_dir" >&2
    exit "$code"
  fi
  if grep -Eqi 'Missing model:|Using default model' "$log"; then
    echo "model closure warning for $condition; artifact is invalid" >&2
    exit 2
  fi
  for stage in 1 2 3 4 5 6; do
    grep -q '"P(B01|XJTL1_'"$stage"')"' "$raw" || {
      echo "missing JTL B01 probe for $condition stage $stage" >&2; exit 3;
    }
    grep -q '"P(B02|XJTL1_'"$stage"')"' "$raw" || {
      echo "missing JTL B02 probe for $condition stage $stage" >&2; exit 3;
    }
  done
  echo "completed $condition"
done

sha256sum "$EXP_DIR"/runs/S*-J-CORRECTED-RERUN/raw/run-01.csv \
  > "$EXP_DIR/analysis/jtl-rerun-raw-sha256sums.txt"
echo "completed JTL probe-only reruns"
