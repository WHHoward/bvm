#!/usr/bin/env bash
set -euo pipefail
echo "Use: python3 analysis/prepare_experiment.py --refresh-head"
echo "Then run each stage as: python3 analysis/execute_pair.py --stage N"
echo "After each pair run: python3 analysis/stage_decision.py --stage N"
