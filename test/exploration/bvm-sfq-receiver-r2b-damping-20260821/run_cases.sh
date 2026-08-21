#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r2b-damping-20260821"
bin="$repo/build/josim-cli"
run_id=run-01
points=(k095-r100 k095-r150 k095-r220 k095-r330)
case_ids=(read1 read0 logical1-read0-control logical0-read0-control)

if [[ $# -eq 1 ]]; then
  points=("$1")
elif [[ $# -ne 0 ]]; then
  echo "usage: $0 [point-id]" >&2
  exit 2
fi

for point in "${points[@]}"; do
  case_id_ok=false
  for known_point in k095-r100 k095-r150 k095-r220 k095-r330; do
    [[ "$point" == "$known_point" ]] && case_id_ok=true
  done
  if [[ "$case_id_ok" != true ]]; then
    echo "unknown point: $point" >&2
    exit 2
  fi
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
