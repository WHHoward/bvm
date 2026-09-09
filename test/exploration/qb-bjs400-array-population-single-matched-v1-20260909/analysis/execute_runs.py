#!/usr/bin/env python3
"""Execute the exact 24 registered BJS400 physical runs once.

This runner never retries a run and never changes a deck.  It records every
command, solver identity, artifact hash and execution status.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"
sys.path.insert(0, str(EXP / "analysis"))
from prepare_experiment import ALL_RUNS, ARRAY_RUNS, SINGLE_RUNS, WORKING_POINTS  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def solver_version() -> str:
    return subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)


def raw_summary(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    if not rows:
        return {"header_count": len(header), "sample_count": 0}
    return {
        "header_count": len(header),
        "sample_count": len(rows),
        "first_timestamp": rows[0][0],
        "last_timestamp": rows[-1][0],
    }


def run_record(run_id: str, head: str, command: list[str], started: str, finished: str, exit_code: int, deck: Path, raw: Path, log: Path) -> dict[str, Any]:
    topology = "ARRAY" if run_id.startswith("ARRAY_") else "SINGLE"
    parts = run_id.split("_")
    if topology == "ARRAY":
        setting = parts[1]
        mask = parts[2]
        active = [index + 1 for index, bit in enumerate(mask) if bit == "1"]
        active_field: dict[str, Any] = {"mask": mask, "active_instances": active}
    else:
        setting = parts[1]
        active = parts[2] == "1"
        active_field = {"final_read_active": active}
    point = WORKING_POINTS[setting]
    return {
        "schema": "bjs400-array-single-run-metadata-v1",
        "experiment_id": EXP.name,
        "run_id": run_id,
        "topology": topology,
        "setting": setting,
        "parameters": point,
        **active_field,
        "started_at_local": started,
        "finished_at_local": finished,
        "git_head_before_run": head,
        "command": command,
        "solver": {
            "path": str(SOLVER),
            "sha256": sha256(SOLVER),
            "version": solver_version(),
        },
        "artifacts": {
            "deck": {"path": str(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
            "raw": {"path": str(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None},
            "log": {"path": str(log), "sha256": sha256(log), "bytes": log.stat().st_size},
        },
        "exit_code": exit_code,
        "execution_status": "RUN_PASS" if exit_code == 0 and raw.is_file() else "RUN_FAIL",
        "raw_immutable": True,
        "parameter_tuning": False,
        "scientific_analysis_performed": False,
        "raw_summary": raw_summary(raw),
    }


def main() -> int:
    preflight_path = EXP / "analysis/preflight.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or preflight.get("exact_physical_solve_count") != 24:
        raise RuntimeError("preflight is not PASS for the exact 24-run matrix")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    preflight_head = preflight.get("head")
    if head != preflight_head:
        changed = set(subprocess.check_output(
            ["git", "diff", "--name-only", f"{preflight_head}..{head}"],
            cwd=REPO,
            text=True,
        ).splitlines())
        allowed_seal = {
            str(EXP.relative_to(REPO) / "PREFLIGHT.md"),
            str(EXP.relative_to(REPO) / "analysis/preflight.json"),
        }
        distance = int(subprocess.check_output(
            ["git", "rev-list", "--count", f"{preflight_head}..{head}"],
            cwd=REPO,
            text=True,
        ).strip())
        if not preflight.get("head_refresh") or distance != 1 or changed != allowed_seal:
            raise RuntimeError(f"HEAD differs from sealed preflight outside seal: {head} != {preflight_head}")
    if not SOLVER.is_file():
        raise RuntimeError(f"missing solver: {SOLVER}")
    started_all = now()
    records: list[dict[str, Any]] = []
    failed: list[str] = []
    for run_id in ALL_RUNS:
        run_dir = EXP / "runs" / run_id
        deck = run_dir / "deck.cir"
        raw = run_dir / "raw.csv"
        log = run_dir / "run.log"
        if not deck.is_file():
            raise RuntimeError(f"missing registered deck: {deck}")
        if raw.exists() or log.exists() or (run_dir / "metadata.json").exists():
            raise RuntimeError(f"refusing to overwrite existing run artifact: {run_dir}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("w", encoding="utf-8") as stream:
            completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
        finished = now()
        record = run_record(run_id, head, command, started, finished, completed.returncode, deck, raw, log)
        metadata = run_dir / "metadata.json"
        metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        records.append(record)
        if record["execution_status"] != "RUN_PASS":
            failed.append(run_id)
    summary = {
        "schema": "bjs400-array-single-execution-v1",
        "experiment_id": EXP.name,
        "started_at_local": started_all,
        "finished_at_local": now(),
        "head": head,
        "preflight_head": preflight["head"],
        "solver_solve_invocations": len(ALL_RUNS),
        "exact_authorized_run_count": len(ALL_RUNS),
        "array_run_count": len(ARRAY_RUNS),
        "single_run_count": len(SINGLE_RUNS),
        "new_physical_solve_count": sum(record["execution_status"] == "RUN_PASS" for record in records),
        "reused_physical_solve_count": 0,
        "unauthorized_extra_solves": 0,
        "failed_runs": failed,
        "run_order": list(ALL_RUNS),
        "runs": records,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "status": "PASS" if not failed else "FAIL",
        "no_retry_performed": True,
    }
    output = EXP / "qa/execution_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "solver_invocations": len(ALL_RUNS), "physical_solve_count": summary["new_physical_solve_count"], "failed_runs": failed, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
