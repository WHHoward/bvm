#!/usr/bin/env bash
set -u

case_name="$1"
exp_dir="$(cd "$(dirname "$0")/.." && pwd)"
bin="$(cd "$exp_dir/../../.." && pwd)/build/josim-cli"
deck="$exp_dir/inputs/$case_name/main.cir"
raw="$exp_dir/raw/$case_name/run.csv"
log_dir="$exp_dir/logs/$case_name"

mkdir -p "$log_dir"
"$bin" -o "$raw" "$deck" >"$log_dir/stdout.txt" 2>"$log_dir/stderr.txt"
rc=$?
printf '%s' "$rc" >"$log_dir/exitcode"
exit "$rc"
