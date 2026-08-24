#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
exp="$repo/test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824"
bin="$repo/build/josim-cli"

if [[ "$#" -lt 2 ]]; then
  echo "usage: $0 WIDTH ROLE [ROLE ...]" >&2
  echo "roles: logical1_read logical0_read logical1_no_read_control logical0_no_read_control" >&2
  exit 2
fi

width="$1"
shift
for role in "$@"; do
  input="$exp/inputs/$width/${role}.cir"
  output="$exp/raw/$width/$role/run-01.csv"
  stdout="$exp/logs/${width}-${role}.stdout.txt"
  stderr="$exp/logs/${width}-${role}.stderr.txt"
  [[ -f "$input" ]] || { echo "missing input: $input" >&2; exit 1; }
  [[ ! -e "$output" ]] || { echo "refusing to overwrite: $output" >&2; exit 1; }
  mkdir -p "$(dirname "$output")"
  "$bin" -a 1 -o "$output" "$input" >"$stdout" 2>"$stderr"
  sha256sum "$output" > "$output.sha256"
done
