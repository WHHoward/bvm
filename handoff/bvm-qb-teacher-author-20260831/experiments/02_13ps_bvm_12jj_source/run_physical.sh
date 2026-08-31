#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
exp="$repo/test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824"
bin="$repo/build/josim-cli"

run_case() {
  local group="$1"
  local case_id="$2"
  local input="$exp/inputs/$group/$case_id-read.cir"
  local output="$exp/raw/$group/$case_id-read/run-01.csv"
  local stdout="$exp/logs/physical-${group}-${case_id}-read.stdout.txt"
  local stderr="$exp/logs/physical-${group}-${case_id}-read.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$output" ]] || { echo "refusing to overwrite: $output" >&2; exit 1; }
  mkdir -p "$(dirname "$output")"
  "$bin" -a 1 -o "$output" "$input" >"$stdout" 2>"$stderr"
  sha256sum "$output" > "$output.sha256"
}

if [[ "$#" -lt 2 ]]; then
  echo "usage: $0 GROUP CASE [CASE ...]" >&2
  exit 2
fi

group="$1"
shift
for case_id in "$@"; do
  run_case "$group" "$case_id"
done
