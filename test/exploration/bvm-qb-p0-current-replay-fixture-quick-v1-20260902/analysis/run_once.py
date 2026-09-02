#!/usr/bin/env python3
"""Run the sole authorized RP JoSIM science run and preserve its receipt."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))
from bvmtools.provenance import file_snapshot, git_snapshot, sha256_file, solver_provenance  # noqa: E402

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "inputs/rp_p0_current_replay.cir"
RAW = ROOT / "raw/run-01.csv"
LOGS = ROOT / "logs"
SOLVER = REPO / "build/josim-cli"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> int:
    if RAW.exists():
        raise RuntimeError(f"refusing to overwrite the sole RP raw: {RAW}")
    if not DECK.is_file():
        raise RuntimeError(f"candidate deck is missing: {DECK}")
    LOGS.mkdir(parents=True, exist_ok=True)
    command = [str(SOLVER), "-a", "1", "-o", str(RAW), str(DECK)]
    started = now()
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    finished = now()
    (LOGS / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (LOGS / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    result: dict[str, object] = {
        "task_id": "BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1",
        "run_id": "RP/run-01",
        "started_at": started,
        "finished_at": finished,
        "command": command,
        "command_cwd": str(REPO),
        "exit_code": completed.returncode,
        "stdout": "logs/stdout.txt",
        "stderr": "logs/stderr.txt",
        "solver": solver_provenance(SOLVER, cwd=REPO),
        "git": git_snapshot(REPO),
    }
    if RAW.is_file():
        result["raw"] = file_snapshot(RAW, relative_to=REPO)
        digest = sha256_file(RAW)
        sidecar = Path(str(RAW) + ".sha256")
        sidecar.write_text(f"{digest}  {RAW.name}\n", encoding="utf-8")
        result["raw_sha256"] = digest
        result["raw_sidecar"] = file_snapshot(sidecar, relative_to=REPO)
    (LOGS / "execution.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return completed.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"run_once: {error}", file=sys.stderr)
        raise SystemExit(2)
