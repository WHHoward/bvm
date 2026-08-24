#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
exp="$repo/test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824"
bin="$repo/build/josim-cli"

run_case() {
  local width="$1"
  local case_id="$2"
  local input="$exp/inputs/phase-a/${width}ps/${case_id}.cir"
  local out="$exp/raw/phase-a/${width}ps/${case_id}/run-01.csv"
  local stdout="$exp/logs/phase-a-${width}ps-${case_id}.stdout.txt"
  local stderr="$exp/logs/phase-a-${width}ps-${case_id}.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; return 1; }
  [[ ! -e "$out" ]] || { echo "refusing to overwrite: $out" >&2; return 1; }
  mkdir -p "$(dirname "$out")"
  "$bin" -a 1 -o "$out" "$input" >"$stdout" 2>"$stderr"
}

for width in 12 15 20; do
  for case_id in logical1-read logical0-read; do
    run_case "$width" "$case_id" &
  done
done
wait

printf '%s\n' "Phase-A JoSIM runs completed for widths 12/15/20 ps." \
  > "$exp/logs/phase-a-execution-complete.txt"
