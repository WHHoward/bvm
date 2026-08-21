#!/usr/bin/env bash
set -euo pipefail
repo=/home/howard/JoSIM
exp="$repo/test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821"
bin="$repo/build/josim-cli"
point="$1"
raw="$exp/raw/$point/run-01.csv"
[[ ! -e "$raw" ]] || { echo "refusing to overwrite: $raw" >&2; exit 1; }
mkdir -p "$exp/raw/$point"
"$bin" -a 1 -o "$raw" "$exp/inputs/$point.cir" >"$exp/logs/$point-run-01.stdout.txt" 2>"$exp/logs/$point-run-01.stderr.txt"
