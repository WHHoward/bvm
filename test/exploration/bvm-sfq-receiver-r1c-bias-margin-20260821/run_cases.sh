#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821"
bin="$repo/build/josim-cli"
run_id=run-01
points=(diff-a010-b006-r100 diff-a010-b007-r100 diff-a010-b008-r100 diff-a010-b009-r100 diff-a010-b010-r100)
case_ids=(read1 read0 logical1-read0-control logical0-read0-control)

if [[ $# -eq 1 ]]; then
  points=("$1")
elif [[ $# -ne 0 ]]; then
  echo "usage: $0 [point-id]" >&2
  exit 2
fi

for point in "${points[@]}"; do
  case_id_ok=false
  for known_point in diff-a010-b006-r100 diff-a010-b007-r100 diff-a010-b008-r100 diff-a010-b009-r100 diff-a010-b010-r100; do
    [[ "$point" == "$known_point" ]] && case_id_ok=true
  done
  "$case_id_ok" || { echo "unknown point: $point" >&2; exit 2; }
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
done
