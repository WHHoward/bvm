#!/usr/bin/env bash
set -euo pipefail
exp_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$exp_dir/analysis/prepare_experiment.py" "$@"
