#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r1-oneshot-20260819"
bin="$repo/build/josim-cli"

if [[ $# -ne 1 ]]; then
  echo "usage: $0 a050-b15|a050-b15-rq100|a050-b15-rq1k|a050-b15-lq10" >&2
  exit 2
fi

op_id=$1
case "$op_id" in
  a050-b15|a050-b15-rq100|a050-b15-rq1k|a050-b15-lq10) ;;
  *) echo "unsupported operating point: $op_id" >&2; exit 2 ;;
esac
case_ids=(read1 read0 logical1-read0-control logical0-read0-control)
for case_id in "${case_ids[@]}"; do
  input="$exp/inputs/$op_id-$case_id.cir"
  raw_dir="$exp/raw/$op_id/$case_id"
  raw="$raw_dir/run-01.csv"
  stdout="$exp/logs/$op_id-$case_id-run-01.stdout.txt"
  stderr="$exp/logs/$op_id-$case_id-run-01.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$raw" ]] || { echo "refusing to overwrite existing raw: $raw" >&2; exit 1; }
  mkdir -p "$raw_dir"
  "$bin" -a 1 -o "$raw" "$input" >"$stdout" 2>"$stderr"
done
