#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(cd -- "$script_dir/../../.." && pwd)
command=all
if [ "$#" -ge 1 ]; then
  command="$1"
fi
exec python3 "$repo_dir/scripts/bvm_qb_qbin_shunt_r20.py" "$command"
