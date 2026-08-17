#!/usr/bin/env bash
# S2-002 immutable 16-run execution.  Run from this directory.
# Uses ONLY /home/howard/JoSIM/build/josim-cli (v2.7.2837d13); PATH forbidden.
set -euo pipefail
CLI=/home/howard/JoSIM/build/josim-cli
ROOT="$(cd "$(dirname "$0")" && pwd)"
LOADS="1 12 25 50"
CASES="init_positive_read init_positive_control init_negative_read init_negative_control"
for case in $CASES; do
  for load in $LOADS; do
    out="$ROOT/raw/$case/${load}ohm"
    mkdir -p "$out"
    (cd "$ROOT/inputs" && \
      "$CLI" "${case}_${load}ohm.cir" -o "../raw/$case/${load}ohm/run-01.csv" \
        > "$out/stdout.txt" 2> "$out/stderr.txt")
    test -s "$out/run-01.csv" || { echo "FAIL: $case/${load}ohm empty CSV"; exit 1; }
    echo "done: $case/${load}ohm ($(wc -l < "$out/run-01.csv") rows)"
  done
done
echo "ALL 16 RUNS COMPLETE"
