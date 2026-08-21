#!/usr/bin/env bash
set -euo pipefail

repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821"
bin="$repo/build/josim-cli"
run_id=run-01

for point in ctrl-nopulse amp20u0 amp30u0 amp40u0 amp50u0; do
  input="$exp/inputs/$point.cir"
  raw_dir="$exp/raw/$point"
  raw="$raw_dir/$run_id.csv"
  stdout="$exp/logs/$point-$run_id.stdout.txt"
  stderr="$exp/logs/$point-$run_id.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$raw" ]] || { echo "refusing to overwrite existing raw: $raw" >&2; exit 1; }
  mkdir -p "$raw_dir"
  "$bin" -a 1 -o "$raw" "$input" >"$stdout" 2>"$stderr"
done
