#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
exp="$repo/test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824"
bin="$repo/build/josim-cli"

if [[ "$#" -eq 0 ]]; then
  set -- logical1_read logical0_read logical1_no_read_control logical0_no_read_control
fi

for role in "$@"; do
  input="$exp/inputs/13/${role}.cir"
  output="$exp/raw/13/${role}/run-01.csv"
  stdout="$exp/logs/13-${role}.stdout.txt"
  stderr="$exp/logs/13-${role}.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$output" ]] || { echo "refusing to overwrite: $output" >&2; exit 1; }
  [[ ! -e "$stdout" ]] || { echo "refusing to overwrite: $stdout" >&2; exit 1; }
  [[ ! -e "$stderr" ]] || { echo "refusing to overwrite: $stderr" >&2; exit 1; }
  mkdir -p "$(dirname "$output")" "$exp/logs"
  "$bin" -a 1 -o "$output" "$input" >"$stdout" 2>"$stderr"
  sha256sum "$output" > "$output.sha256"
done
