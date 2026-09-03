#!/usr/bin/env bash
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
EXP="${REPO}/test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903"
SOLVER="${REPO}/build/josim-cli"
STATES=(0000 1000 0100 0010 0001 1111)

if [[ ! -x "${SOLVER}" ]]; then
  echo "missing executable solver: ${SOLVER}" >&2
  exit 2
fi

python3 "${EXP}/generate_decks.py"

python3 - "${REPO}" <<'PY'
import json
import sys
from pathlib import Path

repo = Path(sys.argv[1])
gate = repo / "test/exploration/research-workflow-tooling-consolidation-v1-20260903/parity/parity.json"
data = json.loads(gate.read_text(encoding="utf-8"))
if data.get("status") != "INFRA_REGRESSION_PASS" or data.get("simulation_invoked") is not False:
    raise SystemExit("PHASE A gate is not INFRA_REGRESSION_PASS with simulation_invoked=false")
PY

failed=0
for state in "${STATES[@]}"; do
  run_dir="${EXP}/runs/${state}"
  deck="${run_dir}/deck.cir"
  raw="${run_dir}/raw.csv"
  log="${run_dir}/run.log"
  metadata="${run_dir}/metadata.json"
  for path in "${raw}" "${log}" "${metadata}"; do
    if [[ -e "${path}" ]]; then
      echo "refusing to overwrite immutable artifact: ${path}" >&2
      exit 3
    fi
  done

  command_text="${SOLVER} -o ${raw} ${deck}"
  set +e
  "${SOLVER}" -o "${raw}" "${deck}" >"${log}" 2>&1
  exit_code=$?
  set -e

  python3 - "${state}" "${deck}" "${raw}" "${log}" "${metadata}" "${exit_code}" "${REPO}" "${command_text}" <<'PY'
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

state, deck_s, raw_s, log_s, metadata_s, exit_s, repo_s, command = sys.argv[1:]
deck = Path(deck_s)
raw = Path(raw_s)
log = Path(log_s)
metadata = Path(metadata_s)
repo = Path(repo_s)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

log_text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
record = {
    "schema": "bvmsim-4bvm-state-position-run-metadata-v1",
    "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    "state": state,
    "source_class": "HISTORICAL_BVMSIM",
    "command": command,
    "exit_code": int(exit_s),
    "deck": str(deck.relative_to(repo)),
    "deck_sha256": digest(deck),
    "raw": str(raw.relative_to(repo)),
    "raw_sha256": digest(raw),
    "run_log": str(log.relative_to(repo)),
    "run_log_sha256": digest(log),
    "solver": {
        "path": str(repo / "build/josim-cli"),
        "sha256": digest(repo / "build/josim-cli"),
    },
    "requested_timestep_ps": 0.1,
    "stop_time_ps": 200,
    "output_start_ps": 45,
    "model_warning_detected": bool(re.search(r"Missing model:|Using default model", log_text, re.I)),
    "artifact_status": "EXECUTION_COMPLETE" if int(exit_s) == 0 and raw.is_file() else "EXECUTION_FAILED",
}
if metadata.exists():
    raise SystemExit(f"refusing to overwrite metadata: {metadata}")
metadata.parent.mkdir(parents=True, exist_ok=True)
metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

  if [[ "${exit_code}" -ne 0 ]]; then
    failed=1
    echo "state ${state}: solver exit ${exit_code}" >&2
  else
    echo "state ${state}: solver exit 0"
  fi
done

exit "${failed}"
