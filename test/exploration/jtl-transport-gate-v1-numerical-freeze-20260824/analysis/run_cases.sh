#!/usr/bin/env bash
set -u

exp_dir="$(cd "$(dirname "$0")/.." && pwd)"
bin="$(cd "$exp_dir/../../.." && pwd)/build/josim-cli"

run_one() {
    local fixture="$1"
    local tag="$2"
    local deck="$exp_dir/inputs/$fixture/$tag/main.cir"
    local raw="$exp_dir/raw/$fixture/$tag/run.csv"
    local log="$exp_dir/logs/$fixture/$tag"
    mkdir -p "$log" "$(dirname "$raw")"
    "$bin" -o "$raw" "$deck" >"$log/stdout.txt" 2>"$log/stderr.txt"
    local rc=$?
    printf '%s\n' "$rc" >"$log/exitcode"
    return "$rc"
}

status=0
for fixture in r11 pulse5-original pulse5-reverse; do
    for tag in 0p025 0p0125 0p00625; do
        run_one "$fixture" "$tag" || status=$?
    done
done
exit "$status"
