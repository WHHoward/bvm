#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
SOLVER="$REPO_ROOT/build/josim-cli"

[[ -x "$SOLVER" ]] || { echo "solver not executable: $SOLVER" >&2; exit 1; }
[[ -z "$(git -C "$REPO_ROOT" status --porcelain)" ]] || {
  echo "working tree must be clean before the new physical runs" >&2
  git -C "$REPO_ROOT" status --short >&2
  exit 1
}

python3 "$SCRIPT_DIR/inputs/generate_decks.py"

conditions=(
  'S0-R-JM2C|direct_10ohm'
  'S1-R-JM2C|direct_10ohm'
  'S0-J-JM2C|six_stage_jtl_plus_10ohm'
  'S1-J-JM2C|six_stage_jtl_plus_10ohm'
)

for item in "${conditions[@]}"; do
  condition=${item%%|*}
  load=${item##*|}
  input="$SCRIPT_DIR/inputs/$condition.cir"
  run_dir="$SCRIPT_DIR/runs/$condition"
  raw="$run_dir/raw/run-01.csv"
  log="$run_dir/logs/run-01.log"

  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$run_dir" ]] || { echo "refusing to overwrite existing run: $run_dir" >&2; exit 1; }
  mkdir -p "$run_dir/raw" "$run_dir/logs"
  cp -- "$input" "$run_dir/deck.cir"
  cmp -- "$input" "$run_dir/deck.cir"

  solver_hash=$(sha256sum "$SOLVER" | awk '{print $1}')
  git_head=$(git -C "$REPO_ROOT" rev-parse HEAD)
  {
    printf 'condition=%s\nload=%s\n' "$condition" "$load"
    printf 'git_head_before_run=%s\n' "$git_head"
    printf 'input=%s\ndeck=%s\nraw=%s\n' "$input" "$run_dir/deck.cir" "$raw"
    printf 'solver=%s\nsolver_version=' "$SOLVER"
    "$SOLVER" --version | tr '\n' ' '
    printf '\nsolver_sha256=%s\n' "$solver_hash"
    printf 'command=%s -a 1 -o %s %s\n' "$SOLVER" "$raw" "$input"
  } > "$run_dir/command.txt"

  set +e
  "$SOLVER" -a 1 -o "$raw" "$input" > "$log" 2>&1
  code=$?
  set -e
  printf 'exit_code=%s\n' "$code" >> "$run_dir/command.txt"

  [[ -s "$raw" ]] || { echo "JoSIM produced no raw for $condition; log preserved" >&2; exit 2; }
  sha256sum "$run_dir/deck.cir" "$raw" > "$run_dir/hashes.sha256"
  if [[ "$code" -ne 0 ]]; then
    echo "JoSIM failed for $condition; raw/log preserved at $run_dir" >&2
    exit "$code"
  fi
  if grep -Eqi 'Missing model:|Using default model' "$log"; then
    echo "model closure warning for $condition; raw/log preserved" >&2
    exit 2
  fi
  echo "completed $condition"
done

sha256sum "$SCRIPT_DIR"/runs/*/raw/run-01.csv > "$SCRIPT_DIR/analysis/raw-sha256sums.txt"
python3 "$SCRIPT_DIR/analysis/preflight.py"
echo "completed JM2-connected single-BVM runs"
