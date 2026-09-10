#!/usr/bin/env bash
set -euo pipefail
echo "Use: python3 analysis/prepare_population.py --refresh-head"
echo "Then: python3 analysis/oracle_regression.py"
echo "Then: python3 analysis/execute_population.py"
echo "Then: python3 analysis/population_analysis.py"
