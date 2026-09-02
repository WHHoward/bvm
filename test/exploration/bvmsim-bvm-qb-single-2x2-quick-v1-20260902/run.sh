#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
SOLVER="$REPO_ROOT/build/josim-cli"
ATTEMPT="${1:-A001}"
ATTEMPT_ROOT="$SCRIPT_DIR/runs/$ATTEMPT"

[[ -x "$SOLVER" ]] || { echo "solver not executable: $SOLVER" >&2; exit 1; }
[[ ! -e "$ATTEMPT_ROOT" ]] || { echo "refusing to overwrite existing attempt: $ATTEMPT_ROOT" >&2; exit 1; }

if [[ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]]; then
  echo "working tree is not clean; commit the preregistered setup before running" >&2
  git -C "$REPO_ROOT" status --short >&2
  exit 1
fi

mkdir -p "$ATTEMPT_ROOT"
printf 'attempt=%s\nsolver=%s\nsolver_sha256=%s\n' \
  "$ATTEMPT" "$SOLVER" "$(sha256sum "$SOLVER" | awk '{print $1}')" \
  > "$ATTEMPT_ROOT/run-manifest.txt"

conditions=(
  'S0-R|s0-r.cir'
  'S1-R|s1-r.cir'
  'S0-J|s0-j.cir'
  'S1-J|s1-j.cir'
)

for item in "${conditions[@]}"; do
  condition=${item%%|*}
  deck_name=${item##*|}
  input="$SCRIPT_DIR/inputs/$deck_name"
  run_dir="$ATTEMPT_ROOT/$condition"
  raw="$run_dir/raw.csv"
  log="$run_dir/run.log"

  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$run_dir" ]] || { echo "refusing to overwrite: $run_dir" >&2; exit 1; }
  mkdir -p "$run_dir"
  cp -- "$input" "$run_dir/deck.cir"
  printf 'condition=%s\ninput=%s\nraw=%s\ncommand=%s -a 1 -o %s %s\n' \
    "$condition" "$input" "$raw" "$SOLVER" "$raw" "$input" \
    > "$run_dir/command.txt"

  set +e
  "$SOLVER" -a 1 -o "$raw" "$input" > "$log" 2>&1
  code=$?
  set -e
  printf 'exit_code=%s\n' "$code" >> "$run_dir/command.txt"
  sha256sum "$run_dir/deck.cir" "$raw" 2>/dev/null > "$run_dir/hashes.sha256" || true
  if [[ "$code" -ne 0 ]]; then
    echo "JoSIM failed for $condition; raw/log preserved at $run_dir" >&2
    exit "$code"
  fi
  echo "completed $condition -> $raw"
done

sha256sum "$ATTEMPT_ROOT"/*/raw.csv > "$ATTEMPT_ROOT/raw-hashes.sha256"
echo "completed attempt $ATTEMPT"
