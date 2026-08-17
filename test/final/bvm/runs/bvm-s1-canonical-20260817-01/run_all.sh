#!/usr/bin/env bash
# S1-002 immutable 12-run execution.  Run from this directory.
# Uses ONLY /home/howard/JoSIM/build/josim-cli (v2.7.2837d13); PATH forbidden.
set -euo pipefail
CLI=/home/howard/JoSIM/build/josim-cli
ROOT="$(cd "$(dirname "$0")" && pwd)"
CASES="init_positive_read init_positive_control init_negative_read init_negative_control"
STEPS="0.05ps 0.025ps 0.0125ps"
for case in $CASES; do
  for step in $STEPS; do
    out="$ROOT/raw/$case/$step"
    mkdir -p "$out"
    (cd "$ROOT/inputs" && \
      "$CLI" "${case}_${step}.cir" -o "../raw/$case/$step/run-01.csv" \
        > "$out/stdout.txt" 2> "$out/stderr.txt")
    test -s "$out/run-01.csv" || { echo "FAIL: $case/$step empty CSV"; exit 1; }
    echo "done: $case/$step ($(wc -l < "$out/run-01.csv") rows)"
  done
done
echo "ALL 12 RUNS COMPLETE"
