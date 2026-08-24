#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
exp="$repo/test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824"
bin="$repo/build/josim-cli"

run_case() {
  local case_id="$1"
  local input="$exp/inputs/phase-b/12jsl-12ps/${case_id}.cir"
  local out="$exp/raw/phase-b/12jsl-12ps/${case_id}/run-01.csv"
  local stdout="$exp/logs/phase-b-12jsl-12ps-${case_id}.stdout.txt"
  local stderr="$exp/logs/phase-b-12jsl-12ps-${case_id}.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; return 1; }
  [[ ! -e "$out" ]] || { echo "refusing to overwrite: $out" >&2; return 1; }
  mkdir -p "$(dirname "$out")"
  "$bin" -a 1 -o "$out" "$input" >"$stdout" 2>"$stderr"
}

run_case logical1-read &
run_case logical0-read &
wait

printf '%s\n' "Phase-B JoSIM runs completed for 12-JSL + W*=12 ps." \
  > "$exp/logs/phase-b-execution-complete.txt"
