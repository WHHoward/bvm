#!/usr/bin/env python3
"""Execute exactly the four authorized delta4 replay solves."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from common import (
    EXP,
    HEAD,
    RUNS,
    SOLVER,
    current_head,
    json_text,
    now_local,
    sha256,
    write_once,
)


def rel(path: Path) -> str:
    return path.relative_to(EXP.parent.parent.parent).as_posix()


def solver_identity() -> dict[str, object]:
    version = subprocess.check_output([str(SOLVER), "--version"], cwd=SOLVER.parent.parent, text=True)
    return {
        "path": SOLVER.relative_to(SOLVER.parent.parent).as_posix(),
        "sha256": sha256(SOLVER),
        "version": version.strip(),
    }


def main() -> int:
    preflight_path = EXP / "analysis/preflight.json"
    registry_path = EXP / "analysis/transformation_registry.json"
    if not preflight_path.is_file() or not registry_path.is_file():
        raise RuntimeError("preflight and transformation registry are required before solve")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise RuntimeError("machine preflight is not PASS")
    if registry.get("head") != HEAD or current_head() != HEAD:
        raise RuntimeError("HEAD changed after preflight")
    if list(registry.get("authorized_runs", {})) != list(RUNS):
        raise RuntimeError("transformation registry run matrix is not exactly the authorized four")
    solver = solver_identity()
    results: dict[str, object] = {}
    for run_id in RUNS:
        run_dir = EXP / "runs" / run_id
        deck = run_dir / "deck.cir"
        raw = run_dir / "raw.csv"
        log = run_dir / "run.log"
        metadata_path = run_dir / "metadata.json"
        if not deck.is_file():
            raise RuntimeError(f"missing registered deck: {deck}")
        if raw.exists() or log.exists() or metadata_path.exists():
            raise RuntimeError(f"refusing to rerun or overwrite artifact: {run_dir}")
        started = now_local()
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        with log.open("x", encoding="utf-8") as output:
            completed = subprocess.run(
                command,
                cwd=SOLVER.parent.parent,
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        finished = now_local()
        artifacts: dict[str, object] = {
            "deck": {
                "path": rel(deck),
                "sha256": sha256(deck),
                "bytes": deck.stat().st_size,
            },
            "log": {
                "path": rel(log),
                "sha256": sha256(log),
                "bytes": log.stat().st_size,
            },
            "raw": {
                "path": rel(raw),
                "exists": raw.exists(),
            },
        }
        if raw.exists():
            artifacts["raw"].update({"sha256": sha256(raw), "bytes": raw.stat().st_size})
        status = "RUN_PASS" if completed.returncode == 0 and raw.exists() else "RUN_FAIL"
        metadata = {
            "schema": "jm2-delta4-replay-run-metadata-v1",
            "experiment_id": EXP.name,
            "run_id": run_id,
            "started_at_local": started,
            "finished_at_local": finished,
            "command": command,
            "solver": solver,
            "artifacts": artifacts,
            "transformation_registry": "analysis/transformation_registry.json",
            "transformation": registry["authorized_runs"][run_id],
            "exit_code": completed.returncode,
            "execution_status": status,
            "raw_immutable": True,
            "controls_rerun": False,
            "parameter_tuning": False,
        }
        write_once(metadata_path, json_text(metadata))
        results[run_id] = metadata
        if status != "RUN_PASS":
            raise RuntimeError(f"replay solve failed for {run_id}; see {log}")
    summary = {
        "schema": "jm2-delta4-replay-execution-summary-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS",
        "physical_run_count": 4,
        "authorized_run_ids": list(RUNS),
        "controls": ["N3_REPLAY", "N4_REPLAY"],
        "controls_rerun": False,
        "cases": results,
    }
    write_once(EXP / "analysis/execution_summary.json", json_text(summary))
    print(json.dumps({"status": "PASS", "physical_run_count": 4, "runs": list(RUNS)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
