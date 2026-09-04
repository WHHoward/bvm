#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)
SOLVER="$REPO_ROOT/build/josim-cli"
PREFLIGHT="$SCRIPT_DIR/analysis/static_preflight.py"
METADATA="$SCRIPT_DIR/analysis/write_metadata.py"

[[ -x "$SOLVER" ]] || { echo "solver is not executable: $SOLVER" >&2; exit 2; }
[[ -z "$(git -C "$REPO_ROOT" status --porcelain --untracked-files=all)" ]] || {
  echo "working tree must be clean before physical runs" >&2
  git -C "$REPO_ROOT" status --short >&2
  exit 3
}

python3 "$PREFLIGHT" --check-only --require-clean >/dev/null
HEAD_BEFORE_RUN=$(git -C "$REPO_ROOT" rev-parse HEAD)

for condition in OLD-NO-HISTORY NEW-WITH-HISTORY; do
  RUN_DIR="$SCRIPT_DIR/runs/$condition"
  DECK="$RUN_DIR/deck.cir"
  RAW="$RUN_DIR/raw.csv"
  LOG="$RUN_DIR/run.log"
  META="$RUN_DIR/metadata.json"
  [[ -f "$DECK" ]] || { echo "missing frozen deck: $DECK" >&2; exit 4; }
  for target in "$RAW" "$LOG" "$META"; do
    [[ ! -e "$target" ]] || { echo "refusing to overwrite immutable artifact: $target" >&2; exit 5; }
  done
  COMMAND_TEXT="$SOLVER -a 1 -o $RAW $DECK"
  set +e
  "$SOLVER" -a 1 -o "$RAW" "$DECK" >"$LOG" 2>&1
  EXIT_CODE=$?
  set -e
  python3 "$METADATA" --condition "$condition" --deck "$DECK" --raw "$RAW" --log "$LOG" --metadata "$META" --solver "$SOLVER" --exit-code "$EXIT_CODE" --git-head-before-run "$HEAD_BEFORE_RUN" --command-text "$COMMAND_TEXT" >/dev/null
  if [[ "$EXIT_CODE" -ne 0 ]]; then
    echo "JoSIM failed for $condition; artifacts preserved" >&2
    exit "$EXIT_CODE"
  fi
  if grep -Eqi 'Missing model:|Using default model' "$LOG"; then
    echo "model closure warning for $condition; artifacts preserved" >&2
    exit 6
  fi
  [[ -s "$RAW" ]] || { echo "empty raw for $condition" >&2; exit 7; }
  echo "completed condition=$condition"
done

echo "completed exactly two authorized crossover JoSIM calls"
