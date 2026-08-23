#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
exp="$repo/test/exploration/paper-sl-l0-20260824"
bin="$repo/build/josim-cli"

cases=(logical1-read logical0-read logical1-read0-control logical0-read0-control)
mkdir -p "$exp/raw" "$exp/logs"
for case_id in "${cases[@]}"; do
  input="$exp/inputs/${case_id}.cir"
  out_dir="$exp/raw/$case_id"
  out="$out_dir/run-01.csv"
  stdout="$exp/logs/${case_id}.stdout.txt"
  stderr="$exp/logs/${case_id}.stderr.txt"
  [[ ! -e "$out" ]] || { echo "refusing to overwrite $out" >&2; exit 1; }
  mkdir -p "$out_dir"
  "$bin" -a 1 -o "$out" "$input" >"$stdout" 2>"$stderr"
done
