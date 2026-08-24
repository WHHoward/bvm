#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
exp="$repo/test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824"
bin="$repo/build/josim-cli"

for case_id in wstar12-logical1-read wstar12-logical0-read wstar12-logical1-read0-control wstar12-logical0-read0-control; do
  input="$exp/inputs/phase-c/${case_id}.cir"
  out="$exp/raw/phase-c/${case_id}/run-01.csv"
  stdout="$exp/logs/phase-c-${case_id}.stdout.txt"
  stderr="$exp/logs/phase-c-${case_id}.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$out" ]] || { echo "refusing to overwrite: $out" >&2; exit 1; }
  mkdir -p "$(dirname "$out")"
  "$bin" -a 1 -o "$out" "$input" >"$stdout" 2>"$stderr" &
done
wait
printf '%s\n' "Phase-C W*=12 ps replay runs completed." > "$exp/logs/phase-c-execution-complete.txt"
