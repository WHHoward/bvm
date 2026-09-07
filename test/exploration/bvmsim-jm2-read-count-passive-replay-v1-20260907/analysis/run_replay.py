#!/usr/bin/env python3
"""Run exactly the three new N2-N4 isolated current-replay cases."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"
CASES = ("n2_replay", "n3_replay", "n4_replay")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def solver_identity() -> dict[str, object]:
    version = subprocess.check_output([str(SOLVER), "--version"], text=True, cwd=REPO)
    return {"path": "build/josim-cli", "sha256": sha256(SOLVER), "version": version.strip()}


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    preflight = json.loads((EXP / "analysis/replay_preflight.json").read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise RuntimeError("replay preflight did not pass")
    solver = solver_identity()
    results: dict[str, object] = {}
    for case in CASES:
        case_dir = EXP / "runs" / case
        deck = case_dir / "deck.cir"
        raw = case_dir / "raw.csv"
        log = case_dir / "run.log"
        metadata_path = case_dir / "metadata.json"
        if not deck.is_file():
            raise RuntimeError(f"missing replay deck: {deck}")
        if raw.exists() or log.exists() or metadata_path.exists():
            raise RuntimeError(f"refusing to rerun or overwrite replay artifact: {case_dir}")
        started = now_local()
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        with log.open("x", encoding="utf-8") as output:
            completed = subprocess.run(command, cwd=REPO, stdout=output, stderr=subprocess.STDOUT, text=True, check=False)
        finished = now_local()
        artifact: dict[str, object] = {
            "deck": {"path": deck.relative_to(REPO).as_posix(), "sha256": sha256(deck), "bytes": deck.stat().st_size},
            "raw": {"path": raw.relative_to(REPO).as_posix(), "exists": raw.exists()},
            "log": {"path": log.relative_to(REPO).as_posix(), "sha256": sha256(log), "bytes": log.stat().st_size},
        }
        if raw.exists():
            artifact["raw"].update({"sha256": sha256(raw), "bytes": raw.stat().st_size})
        metadata = {
            "schema": "jm2-read-count-passive-replay-run-metadata-v1",
            "experiment_id": EXP.name,
            "case": case.upper(),
            "started_at_local": started,
            "finished_at_local": finished,
            "command": command,
            "solver": solver,
            "artifacts": artifact,
            "replay_preflight": "analysis/replay_preflight.json",
            "exit_code": completed.returncode,
            "execution_status": "RUN_PASS" if completed.returncode == 0 and raw.exists() else "RUN_FAIL",
            "raw_immutable": True,
            "parameter_tuning": False,
        }
        write_once(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
        results[case.upper()] = metadata
        if metadata["execution_status"] != "RUN_PASS":
            raise RuntimeError(f"replay run failed: {case}; see {log}")
    summary = {
        "schema": "jm2-read-count-replay-execution-summary-v1",
        "experiment_id": EXP.name,
        "created_at_local": now_local(),
        "status": "PASS",
        "physical_run_count": 3,
        "cases": results,
    }
    write_once(EXP / "analysis/replay_execution_summary.json", json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "PASS", "physical_run_count": 3, "summary": "analysis/replay_execution_summary.json"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
