#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
SOLVER="$REPO_ROOT/build/josim-cli"
PREFLIGHT="$SCRIPT_DIR/analysis/topology_preflight.py"
METADATA="$SCRIPT_DIR/analysis/write_metadata.py"
MASKS=(0000 0001 0010 0100 1000 0011 0111 1100 1110 1111)

[[ -x "$SOLVER" ]] || { echo "solver is not executable: $SOLVER" >&2; exit 2; }
[[ -z "$(git -C "$REPO_ROOT" status --porcelain)" ]] || {
  echo "working tree must be clean before physical runs" >&2
  git -C "$REPO_ROOT" status --short >&2
  exit 3
}

python3 "$PREFLIGHT" --check-only --require-clean
HEAD_BEFORE_RUN=$(git -C "$REPO_ROOT" rev-parse HEAD)

for mask in "${MASKS[@]}"; do
  run_dir="$SCRIPT_DIR/runs/$mask"
  deck="$run_dir/deck.cir"
  raw="$run_dir/raw.csv"
  log="$run_dir/run.log"
  metadata="$run_dir/metadata.json"
  [[ -f "$deck" ]] || { echo "missing deck: $deck" >&2; exit 4; }
  for target in "$raw" "$log" "$metadata"; do
    [[ ! -e "$target" ]] || { echo "refusing to overwrite immutable artifact: $target" >&2; exit 5; }
  done

  command_text="$SOLVER -a 1 -o $raw $deck"
  set +e
  "$SOLVER" -a 1 -o "$raw" "$deck" >"$log" 2>&1
  exit_code=$?
  set -e
  python3 "$METADATA" \
    --mask "$mask" --deck "$deck" --raw "$raw" --log "$log" --metadata "$metadata" \
    --solver "$SOLVER" --exit-code "$exit_code" --git-head-before-run "$HEAD_BEFORE_RUN" \
    --command-text "$command_text"
  if [[ "$exit_code" -ne 0 ]]; then
    echo "JoSIM failed for $mask; raw/log/metadata preserved" >&2
    exit "$exit_code"
  fi
  if grep -Eqi 'Missing model:|Using default model' "$log"; then
    echo "model closure warning for $mask; artifacts preserved" >&2
    exit 6
  fi
  [[ -s "$raw" ]] || { echo "empty raw for $mask" >&2; exit 7; }
  echo "completed mask=$mask"
done

echo "completed exactly ten independent common-SL runs"
