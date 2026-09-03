#!/usr/bin/env bash
set -euo pipefail

EXP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$EXP_DIR/../../.." && pwd)"
SOLVER="$REPO_DIR/build/josim-cli"

if [[ ! -x "$SOLVER" ]]; then
    echo "missing executable solver: $SOLVER" >&2
    exit 2
fi

RUN_IDS=(
    F4_R12_T100 F4_R12_T050 F4_R12_T025 F4_R12_T0125
    F4_R11P5_T100 F4_R11P5_T050 F4_R11P5_T025 F4_R11P5_T0125
    F4_R11_T100 F4_R11_T050 F4_R11_T025 F4_R11_T0125
    S1B_R12_T025_S0 S1B_R12_T025_S1 S1B_R12_T0125_S0 S1B_R12_T0125_S1
    S1B_R11P5_T025_S0 S1B_R11P5_T025_S1 S1B_R11P5_T0125_S0 S1B_R11P5_T0125_S1
    S1B_R11_T025_S0 S1B_R11_T025_S1 S1B_R11_T0125_S0 S1B_R11_T0125_S1
)

failures=0
for run_id in "${RUN_IDS[@]}"; do
    deck_rel="test/exploration/bvm-qb-rj1-timestep-robustness-v1-20260903/runs/$run_id/deck.cir"
    raw_rel="test/exploration/bvm-qb-rj1-timestep-robustness-v1-20260903/runs/$run_id/raw/run-01.csv"
    deck="$REPO_DIR/$deck_rel"
    raw="$REPO_DIR/$raw_rel"
    run_dir="$EXP_DIR/runs/$run_id"
    mkdir -p "$run_dir/raw" "$run_dir/analysis" "$run_dir/plots" "$run_dir/logs"

    if [[ ! -f "$deck" ]]; then
        echo "missing deck: $deck" >&2
        failures=$((failures + 1))
        continue
    fi
    if [[ -e "$raw" ]]; then
        echo "refusing to overwrite existing raw: $raw" >&2
        failures=$((failures + 1))
        continue
    fi

    echo "running $run_id"
    set +e
    (
        cd "$REPO_DIR"
        "$SOLVER" -o "$raw_rel" "$deck_rel"
    ) >"$run_dir/logs/run-01.log" 2>&1
    exit_code=$?
    set -e
    {
        echo "command: ./build/josim-cli -o $raw_rel $deck_rel"
        echo "exit_code: $exit_code"
        if [[ -f "$raw" ]]; then
            echo "raw_sha256: $(sha256sum "$raw" | awk '{print $1}')"
        else
            echo "raw_sha256: MISSING"
        fi
    } >"$run_dir/logs/command-01.txt"
    if [[ "$exit_code" -ne 0 ]]; then
        echo "FAILED $run_id (exit $exit_code)" >&2
        failures=$((failures + 1))
    else
        echo "completed $run_id"
    fi
done

if [[ "$failures" -ne 0 ]]; then
    echo "$failures run(s) failed or were refused; raw/log history was preserved" >&2
    exit 1
fi

echo "all ${#RUN_IDS[@]} runs completed"
