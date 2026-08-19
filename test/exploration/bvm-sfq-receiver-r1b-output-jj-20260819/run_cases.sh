#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819"
bin="$repo/build/josim-cli"

if [[ $# -ne 1 || "$1" != "l010-b07-rd100-loop" ]]; then
  echo "usage: $0 l010-b07-rd100-loop" >&2
  exit 2
fi

point=$1
case_ids=(read1 read0 logical1-read0-control logical0-read0-control)
for case_id in "${case_ids[@]}"; do
  input="$exp/inputs/$point-$case_id.cir"
  raw_dir="$exp/raw/$point/$case_id"
  raw="$raw_dir/run-01.csv"
  stdout="$exp/logs/$point-$case_id-run-01.stdout.txt"
  stderr="$exp/logs/$point-$case_id-run-01.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$raw" ]] || { echo "refusing to overwrite existing raw: $raw" >&2; exit 1; }
  mkdir -p "$raw_dir"
  "$bin" -a 1 -o "$raw" "$input" >"$stdout" 2>"$stderr"
done
