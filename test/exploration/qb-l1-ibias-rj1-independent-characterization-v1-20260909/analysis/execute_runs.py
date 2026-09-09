#!/usr/bin/env python3
"""Execute exactly the 12 registered new physical solves.

This runner never retries, tunes, ranks, analyzes, or adds a point.  A solver
failure is recorded and the remaining authorized matrix is still attempted so
one abnormal family point does not silently cancel the registered family.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"
RUNS = (
    ("L1_1P2", "L1", 12.0, 1.2, 250.0),
    ("L1_1P4", "L1", 12.0, 1.4, 250.0),
    ("L1_1P6", "L1", 12.0, 1.6, 250.0),
    ("L1_1P8", "L1", 12.0, 1.8, 250.0),
    ("IB_230", "IBias", 12.0, 2.0, 230.0),
    ("IB_240", "IBias", 12.0, 2.0, 240.0),
    ("IB_260", "IBias", 12.0, 2.0, 260.0),
    ("IB_270", "IBias", 12.0, 2.0, 270.0),
    ("RJ1_8", "RJ1", 8.0, 2.0, 250.0),
    ("RJ1_10", "RJ1", 10.0, 2.0, 250.0),
    ("RJ1_14", "RJ1", 14.0, 2.0, 250.0),
    ("RJ1_16", "RJ1", 16.0, 2.0, 250.0),
)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_summary(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        count = 0
        first = None
        last = None
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) != len(header):
                raise RuntimeError(f"malformed raw row {count + 1}: {path}")
            count += 1
            first = row[0] if first is None else first
            last = row[0]
    return {
        "header_count": len(header),
        "sample_count": count,
        "first_timestamp": first,
        "last_timestamp": last,
    }


def write_once(path: Path, record: dict[str, object]) -> None:
    content = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") != content:
            raise RuntimeError(f"refusing to overwrite run metadata: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    preflight_path = EXP / "analysis" / "preflight.json"
    if not preflight_path.is_file():
        raise RuntimeError("machine preflight is missing; solver invocation forbidden")
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS":
        raise RuntimeError("machine preflight is not PASS; solver invocation forbidden")
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    preflight_head = preflight.get("head")
    head_relation = "EXACT_PREFLIGHT_HEAD"
    if current_head != preflight_head:
        changed = set(subprocess.check_output(
            ["git", "diff", "--name-only", f"{preflight_head}..{current_head}"],
            cwd=REPO,
            text=True,
        ).splitlines())
        allowed_seal = {
            str(EXP.relative_to(REPO) / "PREFLIGHT.md"),
            str(EXP.relative_to(REPO) / "analysis/preflight.json"),
        }
        distance = int(subprocess.check_output(
            ["git", "rev-list", "--count", f"{preflight_head}..{current_head}"],
            cwd=REPO,
            text=True,
        ).strip())
        if not preflight.get("head_refresh") or distance != 1 or changed != allowed_seal:
            raise RuntimeError(
                "HEAD changed after preflight outside the permitted preflight-only seal: "
                f"{current_head} != {preflight_head}; changed={sorted(changed)}"
            )
        head_relation = "PREFLIGHT_ONLY_SEAL_COMMIT"
    if not SOLVER.is_file():
        raise RuntimeError(f"solver missing: {SOLVER}")
    solver_version = subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)
    records: list[dict[str, object]] = []
    for run_id, family, rj1, l1, ibias in RUNS:
        run_dir = EXP / "runs" / run_id
        deck = run_dir / "deck.cir"
        raw = run_dir / "raw.csv"
        log = run_dir / "run.log"
        metadata_path = run_dir / "metadata.json"
        if not deck.is_file():
            raise RuntimeError(f"registered deck is missing: {deck}")
        if any(path.exists() for path in (raw, log, metadata_path)):
            raise RuntimeError(f"refusing to overwrite existing run output: {run_id}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        exit_code: int | None = None
        exception: str | None = None
        run_dir.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8") as log_stream:
            log_stream.write("COMMAND: " + " ".join(command) + "\n")
            log_stream.write("RUN_ID: " + run_id + "\n")
            log_stream.write("FAMILY: " + family + "\n")
            log_stream.write("HEAD: " + current_head + "\n")
            try:
                completed = subprocess.run(command, cwd=run_dir, stdout=log_stream, stderr=subprocess.STDOUT, check=False)
                exit_code = completed.returncode
            except Exception as exc:  # preserve this attempt; no retry
                exception = repr(exc)
        finished = now()
        raw_record = {
            "path": str(raw),
            "exists": raw.is_file(),
            "sha256": sha256(raw) if raw.is_file() else None,
            "bytes": raw.stat().st_size if raw.is_file() else None,
        }
        record = {
            "schema": "qb-l1-ibias-rj1-independent-run-metadata-v1",
            "experiment_id": EXP.name,
            "run_id": run_id,
            "family": family,
            "run_directory": str(run_dir),
            "started_at_local": started,
            "finished_at_local": finished,
            "git_head_before_run": current_head,
            "command": command,
            "solver": {"path": str(SOLVER), "sha256": sha256(SOLVER), "version": solver_version},
            "parameters": {"RJ1_ohm": rj1, "L1_pH": l1, "IBias_uA": ibias, "exactly_one_intervention": family},
            "artifacts": {
                "deck": {"path": str(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
                "raw": raw_record,
                "log": {"path": str(log), "sha256": sha256(log), "bytes": log.stat().st_size},
            },
            "exit_code": exit_code,
            "execution_status": "RUN_PASS" if exit_code == 0 and exception is None and raw.is_file() else "RUN_FAIL",
            "raw_immutable": True,
            "parameter_tuning": False,
            "scientific_analysis_performed": False,
            "exception": exception,
            "raw_summary": raw_summary(raw),
        }
        write_once(metadata_path, record)
        records.append(record)

    failures = [record["run_id"] for record in records if record["execution_status"] != "RUN_PASS"]
    summary = {
        "schema": "qb-l1-ibias-rj1-independent-execution-v1",
        "experiment_id": EXP.name,
        "started_at_local": records[0]["started_at_local"],
        "finished_at_local": now(),
        "head": current_head,
        "preflight_head": preflight_head,
        "head_relation_to_preflight": head_relation,
        "solver_solve_invocations": len(records),
        "exact_authorized_run_count": len(RUNS),
        "new_physical_solve_count": len(records),
        "reused_physical_solve_count": 0,
        "unauthorized_extra_solves": 0,
        "run_order": [record["run_id"] for record in records],
        "runs": records,
        "status": "RUN_PASS" if not failures else "RUN_FAIL",
        "failed_runs": failures,
        "automatic_followup": False,
        "scientific_analysis_performed": False,
        "next_action": "mechanical QA only; STOP on package failure; no retry or tuning",
    }
    write_once(EXP / "qa" / "execution_summary.json", summary)
    print(json.dumps({"status": summary["status"], "new_physical_solve_count": len(records), "failed_runs": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
