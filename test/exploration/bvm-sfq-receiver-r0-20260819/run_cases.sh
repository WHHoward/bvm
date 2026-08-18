#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r0-20260819"
bin="$repo/build/josim-cli"

cases=(read1 read0 logical1-read0-control logical0-read0-control)
for case_id in "${cases[@]}"; do
  mkdir -p "$exp/raw/$case_id"
  "$bin" -o "$exp/raw/$case_id/run-01.csv" "$exp/inputs/$case_id.cir" \
    >"$exp/logs/$case_id.stdout.txt" \
    2>"$exp/logs/$case_id.stderr.txt"
done
