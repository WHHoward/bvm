#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r0b-20260819"
bin="$repo/build/josim-cli"

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 <a050-b15|a050-b20|a045-b20|a040-b20> [run-id]" >&2
  exit 2
fi

op_id=$1
run_id=${2:-run-01}
case "$op_id" in
  a050-b15|a050-b20|a045-b20|a040-b20) ;;
  *) echo "unsupported operating point: $op_id" >&2; exit 2 ;;
esac

case_ids=(read1 read0 logical1-read0-control logical0-read0-control)
for case_id in "${case_ids[@]}"; do
  input="$exp/inputs/$op_id-$case_id.cir"
  raw_dir="$exp/raw/$op_id/$case_id"
  raw="$raw_dir/$run_id.csv"
  stdout="$exp/logs/$op_id-$case_id-$run_id.stdout.txt"
  stderr="$exp/logs/$op_id-$case_id-$run_id.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$raw" ]] || { echo "refusing to overwrite existing raw: $raw" >&2; exit 1; }
  mkdir -p "$raw_dir"
  "$bin" -o "$raw" "$input" >"$stdout" 2>"$stderr"
done
