#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r2a-coupling-20260821"
points=(
  "diff-a010-b007-k060:0.60"
  "diff-a010-b007-k070:0.70"
  "diff-a010-b007-k080:0.80"
  "diff-a010-b007-k090:0.90"
  "diff-a010-b007-k095:0.95"
)

if [[ $# -ne 0 ]]; then
  echo "usage: $0" >&2
  exit 2
fi

for item in "${points[@]}"; do
  point=${item%%:*}
  coupling=${item##*:}
  primary="analysis/$point-analysis.json"
  crosscheck="analysis/$point-crosscheck.json"
  [[ ! -e "$exp/$primary" ]] || { echo "refusing to overwrite $primary" >&2; exit 1; }
  [[ ! -e "$exp/$crosscheck" ]] || { echo "refusing to overwrite $crosscheck" >&2; exit 1; }
  POINT_ID="$point" COUPLING_K="$coupling" OUT_BIAS_UA=7.0 ANALYSIS_OUTPUT="$primary" \
    python3 "$exp/analyze_r2a.py" \
    | tee "$exp/logs/$point-analysis.stdout.txt"
  POINT_ID="$point" PRIMARY_ANALYSIS="$primary" CROSSCHECK_OUTPUT="$crosscheck" \
    python3 "$exp/analysis/independent_crosscheck.py" \
    | tee "$exp/logs/$point-crosscheck.stdout.txt"
done
