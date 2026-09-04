#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
SOLVER="$REPO_ROOT/build/josim-cli"
STATIC_PREFLIGHT="$SCRIPT_DIR/analysis/static_preflight.py"
METADATA_WRITER="$SCRIPT_DIR/analysis/run_metadata.py"

[[ -x "$SOLVER" ]] || { echo "solver not executable: $SOLVER" >&2; exit 1; }
[[ -x "$SCRIPT_DIR/generate_decks.py" ]] || { echo "generator not executable" >&2; exit 1; }
[[ -z "$(git -C "$REPO_ROOT" status --porcelain)" ]] || {
  echo "working tree must be clean before the new physical runs" >&2
  git -C "$REPO_ROOT" status --short >&2
  exit 1
}

python3 "$STATIC_PREFLIGHT" --check-only --require-clean

HEAD_BEFORE_RUN=$(git -C "$REPO_ROOT" rev-parse HEAD)

conditions=(
  'S0-J-RLOOP|0'
  'S1-J-RLOOP|1'
)

for item in "${conditions[@]}"; do
  condition=${item%%|*}
  state=${item##*|}
  run_dir="$SCRIPT_DIR/runs/$condition"
  deck="$run_dir/deck.cir"
  raw="$run_dir/raw.csv"
  log="$run_dir/run.log"
  metadata="$run_dir/metadata.json"

  [[ -f "$deck" ]] || { echo "missing frozen executed deck: $deck" >&2; exit 2; }
  [[ ! -e "$raw" ]] || { echo "refusing to overwrite raw: $raw" >&2; exit 2; }
  [[ ! -e "$log" ]] || { echo "refusing to overwrite log: $log" >&2; exit 2; }
  [[ ! -e "$metadata" ]] || { echo "refusing to overwrite metadata: $metadata" >&2; exit 2; }
  mkdir -p "$run_dir"

  command=("$SOLVER" -a 1 -o "$raw" "$deck")
  set +e
  "${command[@]}" > "$log" 2>&1
  exit_code=$?
  set -e

  python3 "$METADATA_WRITER" "$condition" "$state" "$exit_code" "$deck" "$raw" "$log" "$SOLVER" \
    --git-head-before-run "$HEAD_BEFORE_RUN" --command -- "${command[@]}"

  if [[ "$exit_code" -ne 0 ]]; then
    echo "JoSIM failed for $condition; raw/log/metadata preserved" >&2
    exit "$exit_code"
  fi
  if grep -Eqi 'Missing model:|Using default model' "$log"; then
    echo "model closure warning for $condition; artifacts preserved" >&2
    exit 2
  fi
  [[ -s "$raw" ]] || { echo "empty raw for $condition" >&2; exit 2; }
  echo "completed $condition"
done

echo "completed exactly two authorized JM2-connected single-BVM R-LOOP runs"
