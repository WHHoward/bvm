#!/usr/bin/env python3
"""Execute exactly the two preregistered physical runs, once each."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def now_local() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_one(kind: str) -> dict[str, object]:
    run_dir = EXP / "runs" / kind
    deck = run_dir / "deck.cir"
    raw = run_dir / "raw.csv"
    log = run_dir / "run.log"
    metadata = run_dir / "metadata.json"
    for path in (deck,):
        if not path.is_file():
            raise RuntimeError(f"missing deck: {path}")
    if raw.exists() or log.exists() or metadata.exists():
        raise RuntimeError(f"refusing to overwrite existing run artifact in {run_dir}")
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now_local()
    exit_code: int
    exception: str | None = None
    try:
        with log.open("x", encoding="utf-8") as handle:
            completed = subprocess.run(command, cwd=REPO, stdout=handle, stderr=subprocess.STDOUT, check=False)
        exit_code = int(completed.returncode)
    except Exception as exc:  # preserve a metadata record for tooling failure
        exit_code = 127
        exception = repr(exc)
    finished = now_local()
    record: dict[str, object] = {
        "schema": "jm2-single-vs-4bvm-shared-sl-run-metadata-v1",
        "experiment_id": EXP.name,
        "fixture": kind.upper(),
        "started_at_local": started,
        "finished_at_local": finished,
        "git_head_at_run": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "command": command,
        "solver": {
            "path": rel(SOLVER),
            "sha256": sha256(SOLVER),
            "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True),
        },
        "artifacts": {
            "deck": {"path": rel(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
            "raw": {"path": rel(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None},
            "log": {"path": rel(log), "exists": log.is_file(), "sha256": sha256(log) if log.is_file() else None, "bytes": log.stat().st_size if log.is_file() else None},
        },
        "exit_code": exit_code,
        "execution_status": "RUN_PASS" if exit_code == 0 else "RUN_FAIL",
        "raw_immutable": True,
        "parameter_tuning": False,
        "exception": exception,
    }
    metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"fixture": kind.upper(), "status": record["execution_status"], "exit_code": exit_code, "raw": record["artifacts"]["raw"]}, ensure_ascii=False))
    return record


def main() -> int:
    preflight = EXP / "analysis/topology_preflight.json"
    if not preflight.is_file():
        raise RuntimeError("run preflight before executing physical fixtures")
    preflight_record = json.loads(preflight.read_text(encoding="utf-8"))
    if preflight_record.get("status") != "PASS":
        raise RuntimeError("topology preflight did not PASS; no physical run started")
    if not SOLVER.is_file():
        raise RuntimeError(f"missing solver: {SOLVER}")
    records: dict[str, object] = {}
    for kind in ("single", "array"):
        record = run_one(kind)
        records[kind] = record
        if record["execution_status"] != "RUN_PASS":
            print("A run failed; preserve its artifact and stop before starting a second physical run.", file=sys.stderr)
            return 1
    summary = {
        "schema": "jm2-single-vs-4bvm-shared-sl-execution-summary-v1",
        "experiment_id": EXP.name,
        "completed_at_local": now_local(),
        "physical_run_count": 2,
        "runs": {kind: {"execution_status": record["execution_status"], "raw_sha256": record["artifacts"]["raw"]["sha256"]} for kind, record in records.items()},
        "status": "PASS",
    }
    summary_path = EXP / "analysis/execution_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
