#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821"
points=(
  "diff-a010-b006-r100:6"
  "diff-a010-b007-r100:7"
  "diff-a010-b008-r100:8"
  "diff-a010-b009-r100:9"
  "diff-a010-b010-r100:10"
)

if [[ $# -ne 0 ]]; then
  echo "usage: $0" >&2
  exit 2
fi

for item in "${points[@]}"; do
  point=${item%%:*}
  bias=${item##*:}
  primary="analysis/$point-analysis.json"
  crosscheck="analysis/$point-crosscheck.json"
  [[ ! -e "$exp/$primary" ]] || { echo "refusing to overwrite $primary" >&2; exit 1; }
  [[ ! -e "$exp/$crosscheck" ]] || { echo "refusing to overwrite $crosscheck" >&2; exit 1; }
  POINT_ID="$point" OUT_BIAS_UA="$bias" ANALYSIS_OUTPUT="$primary" \
    python3 "$exp/analyze_r1c.py" \
    | tee "$exp/logs/$point-analysis.stdout.txt"
  POINT_ID="$point" PRIMARY_ANALYSIS="$primary" CROSSCHECK_OUTPUT="$crosscheck" \
    python3 "$exp/analysis/independent_crosscheck.py" \
    | tee "$exp/logs/$point-crosscheck.stdout.txt"
done
