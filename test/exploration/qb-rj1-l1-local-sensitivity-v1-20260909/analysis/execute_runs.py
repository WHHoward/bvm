#!/usr/bin/env python3
"""Execute exactly the five registered physical solves after preflight PASS."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"
EXPECTED_HEAD = "08c7320bdd6e871d9b9536dcd27f5e8b2b0d5604"
RUNS = (
    ("NOMINAL", "nominal", 12.0, 2.0),
    ("L1_DOWN", "l1_down", 12.0, 1.9),
    ("L1_UP", "l1_up", 12.0, 2.1),
    ("RJ1_UP_05", "rj1_up_05", 12.5, 2.0),
    ("RJ1_UP_10", "rj1_up_10", 13.0, 2.0),
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.write_text(content, encoding="utf-8")


def raw_summary(path: Path) -> dict[str, object]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        count = 0
        first = None
        last = None
        for row in reader:
            count += 1
            if len(row) != len(header):
                raise RuntimeError(f"malformed raw row {count}: {path}")
            if first is None:
                first = row[0]
            last = row[0]
    return {"header_count": len(header), "sample_count": count, "time_start": first, "time_end": last}


def main() -> int:
    preflight_path = EXP / "analysis/preflight.json"
    if not preflight_path.is_file():
        raise RuntimeError("preflight record is missing")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise RuntimeError("machine preflight is not PASS; solver invocation forbidden")
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if current_head != EXPECTED_HEAD or current_head != preflight.get("head"):
        raise RuntimeError(f"HEAD changed after preflight: {current_head}")
    if not SOLVER.is_file():
        raise RuntimeError(f"solver missing: {SOLVER}")

    solver_version = subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)
    records: list[dict[str, object]] = []
    for run_id, directory, rj1, l1 in RUNS:
        run_dir = EXP / "runs" / directory
        deck = run_dir / "deck.cir"
        raw = run_dir / "raw.csv"
        log = run_dir / "run.log"
        metadata_path = run_dir / "metadata.json"
        if not deck.is_file():
            raise RuntimeError(f"missing registered deck: {deck}")
        for output in (raw, log, metadata_path):
            if output.exists():
                raise RuntimeError(f"refusing to overwrite existing run output: {output}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        exit_code = None
        exception = None
        with log.open("w", encoding="utf-8") as log_stream:
            log_stream.write("COMMAND: " + " ".join(command) + "\n")
            log_stream.write("RUN_ID: " + run_id + "\n")
            log_stream.write("HEAD: " + current_head + "\n")
            log_stream.flush()
            try:
                completed = subprocess.run(command, cwd=run_dir, stdout=log_stream, stderr=subprocess.STDOUT, check=False)
                exit_code = completed.returncode
            except Exception as exc:  # preserve the attempt record before surfacing the tool failure
                exception = repr(exc)
        finished = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        raw_exists = raw.is_file()
        raw_record: dict[str, object] = {
            "path": str(raw),
            "exists": raw_exists,
            "sha256": sha256(raw) if raw_exists else None,
            "bytes": raw.stat().st_size if raw_exists else None,
        }
        summary = raw_summary(raw) if raw_exists and exit_code == 0 else None
        record = {
            "schema": "qb-rj1-l1-local-sensitivity-run-metadata-v1",
            "experiment_id": EXP.name,
            "run_id": run_id,
            "run_directory": str(run_dir),
            "started_at_local": started,
            "finished_at_local": finished,
            "git_head_before_run": current_head,
            "command": command,
            "solver": {"path": str(SOLVER), "sha256": sha256(SOLVER), "version": solver_version},
            "parameters": {"RJ1_ohm": rj1, "L1_pH": l1, "parameterization": "BQ_parameterized.cir"},
            "artifacts": {
                "deck": {"path": str(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
                "raw": raw_record,
                "log": {"path": str(log), "sha256": sha256(log), "bytes": log.stat().st_size},
            },
            "exit_code": exit_code,
            "execution_status": "RUN_PASS" if exit_code == 0 and exception is None and raw_exists else "RUN_FAIL",
            "raw_immutable": True,
            "parameter_tuning": False,
            "exception": exception,
            "raw_summary": summary,
        }
        write_once(metadata_path, json.dumps(record, indent=2, ensure_ascii=False) + "\n")
        records.append(record)
        if record["execution_status"] != "RUN_PASS":
            summary_record = {
                "schema": "qb-rj1-l1-local-sensitivity-execution-v1",
                "experiment_id": EXP.name,
                "started_at_local": started,
                "finished_at_local": finished,
                "head": current_head,
                "exact_authorized_run_count": len(RUNS),
                "runs_completed_before_stop": records,
                "status": "RUN_FAIL",
                "next_action": "STOP; preserve failed attempt; no automatic retry or follow-up",
            }
            write_once(EXP / "analysis/execution_summary.json", json.dumps(summary_record, indent=2, ensure_ascii=False) + "\n")
            print(json.dumps({"status": "RUN_FAIL", "failed_run": run_id, "completed_count": len(records)}, ensure_ascii=False))
            return 1

    finished_all = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    summary_record = {
        "schema": "qb-rj1-l1-local-sensitivity-execution-v1",
        "experiment_id": EXP.name,
        "started_at_local": records[0]["started_at_local"],
        "finished_at_local": finished_all,
        "head": current_head,
        "solver_solve_invocations": len(records),
        "exact_authorized_run_count": len(RUNS),
        "run_order": [run_id for run_id, _, _, _ in RUNS],
        "runs": records,
        "status": "RUN_PASS",
        "automatic_followup": False,
        "next_action": "raw QA, registered analysis and visualization only; stop at AWAITING_USER_REVIEW",
    }
    write_once(EXP / "analysis/execution_summary.json", json.dumps(summary_record, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "RUN_PASS", "solver_solve_invocations": len(records), "run_order": summary_record["run_order"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
