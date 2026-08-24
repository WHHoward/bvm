#!/usr/bin/env bash
set -u

exp_dir="$(cd "$(dirname "$0")/.." && pwd)"
bin="$(cd "$exp_dir/../../.." && pwd)/build/josim-cli"
status=0

for fixture in r11 pulse5-original pulse5-reverse; do
    for tag in 0p025 0p0125 0p00625; do
        deck="$exp_dir/inputs/$fixture/$tag/main.cir"
        raw="$exp_dir/raw/$fixture/$tag/run.csv"
        log="$exp_dir/logs/$fixture/$tag"
        mkdir -p "$log" "$(dirname "$raw")"
        "$bin" -o "$raw" "$deck" >"$log/stdout.txt" 2>"$log/stderr.txt"
        rc=$?
        printf '%s\n' "$rc" >"$log/exitcode"
        if [ "$rc" -ne 0 ]; then
            status="$rc"
        fi
    done
done
exit "$status"
