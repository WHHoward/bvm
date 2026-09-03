#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
EXP="${REPO}/test/exploration/bvmsim-4bvm-jm2-connected-state-position-ab-v1-20260903"
SOLVER="${REPO}/build/josim-cli"
STATES=(0000 1000 0100 0010 0001 1111)

if [[ ! -x "${SOLVER}" ]]; then
  echo "missing executable solver: ${SOLVER}" >&2
  exit 2
fi
if [[ -n "$(git -C "${REPO}" status --porcelain)" ]]; then
  echo "refusing physical run: working tree is not clean" >&2
  exit 3
fi

python3 "${EXP}/analysis/static_preflight.py" --check-only --require-clean

failed=0
for state in "${STATES[@]}"; do
  run_dir="${EXP}/runs/${state}"
  deck="${run_dir}/deck.cir"
  raw="${run_dir}/raw.csv"
  log="${run_dir}/run.log"
  metadata="${run_dir}/metadata.json"
  if [[ ! -f "${deck}" ]]; then
    echo "missing deck: ${deck}" >&2
    exit 4
  fi
  for path in "${raw}" "${log}" "${metadata}"; do
    if [[ -e "${path}" ]]; then
      echo "refusing to overwrite immutable artifact: ${path}" >&2
      exit 5
    fi
  done

  command_text="${SOLVER} -o ${raw} ${deck}"
  if "${SOLVER}" -o "${raw}" "${deck}" >"${log}" 2>&1; then
    exit_code=0
  else
    exit_code=$?
  fi
  python3 "${EXP}/analysis/write_run_metadata.py" \
    --repo "${REPO}" --state "${state}" --deck "${deck}" --raw "${raw}" \
    --log "${log}" --metadata "${metadata}" --exit-code "${exit_code}" \
    --command-text "${command_text}"
  if [[ "${exit_code}" -ne 0 ]]; then
    failed=1
    echo "state ${state}: solver exit ${exit_code}" >&2
  else
    echo "state ${state}: solver exit 0"
  fi
done

exit "${failed}"
