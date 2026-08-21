#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r1b-area008-20260821"
bin="$repo/build/josim-cli"
point=diff-a008-b07-r100-series-return

if [[ $# -ne 1 || "$1" != "$point" ]]; then
  echo "usage: $0 $point" >&2
  exit 2
fi

case_ids=(read1 read0 logical1-read0-control logical0-read0-control)
run_id=run-01
for case_id in "${case_ids[@]}"; do
  input="$exp/inputs/$point-$case_id.cir"
  raw_dir="$exp/raw/$point/$case_id"
  raw="$raw_dir/$run_id.csv"
  stdout="$exp/logs/$point-$case_id-$run_id.stdout.txt"
  stderr="$exp/logs/$point-$case_id-$run_id.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$raw" ]] || { echo "refusing to overwrite existing raw: $raw" >&2; exit 1; }
  mkdir -p "$raw_dir"
  "$bin" -a 1 -o "$raw" "$input" >"$stdout" 2>"$stderr"
done
