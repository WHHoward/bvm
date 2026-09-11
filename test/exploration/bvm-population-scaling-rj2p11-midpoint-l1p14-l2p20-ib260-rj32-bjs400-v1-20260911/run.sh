#!/usr/bin/env bash
set -euo pipefail
echo "Use: python3 analysis/prepare_midpoint.py"
echo "Then: python3 analysis/oracle_regression.py"
echo "Then: python3 analysis/execute_midpoint.py"
echo "Then: python3 analysis/response_analysis.py"
echo "Then: python3 analysis/independent_midpoint_review.py"
echo "Then: python3 analysis/render_flat_midpoint.py"
echo "Then: python3 analysis/visualization_qa.py"
echo "Then: python3 analysis/package_midpoint.py"
