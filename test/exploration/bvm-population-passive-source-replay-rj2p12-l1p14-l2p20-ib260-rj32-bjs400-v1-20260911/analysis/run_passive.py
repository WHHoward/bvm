#!/usr/bin/env python3
"""Execute exactly the three registered passive source captures."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
SOLVER = REPO / "build/josim-cli"
CASES = ("PASSIVE_N2_0011", "PASSIVE_N3_0111", "PASSIVE_N4_1111")
MASKS = {"PASSIVE_N2_0011": "0011", "PASSIVE_N3_0111": "0111", "PASSIVE_N4_1111": "1111"}
SOLVER_SHA256 = "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_summary(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        first = next(reader)
        last = first
        count = 1
        for row in reader:
            last = row
            count += 1
    return {"header_count": len(header), "sample_count": count, "first_timestamp": first[0], "last_timestamp": last[0]}


def solver_identity() -> dict[str, Any]:
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("registered solver identity changed")
    return {"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}


def main() -> int:
    preflight_path = EXP / "analysis/preflight.json"
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    current_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if preflight.get("status") != "PASS" or preflight.get("authorized_physical_solve_count") != 6 or preflight.get("physical_solve_count_before_preflight") != 0:
        raise RuntimeError("passive execution gate is not a PASS six-solve preflight")
    if current_head != preflight.get("head_at_preflight"):
        raise RuntimeError(f"HEAD changed after preflight seal: {current_head} != {preflight.get('head_at_preflight')}")
    solver = solver_identity()
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for case in CASES:
        run_dir = EXP / "runs" / case
        deck = run_dir / "deck.cir"
        raw = run_dir / "raw.csv"
        log = run_dir / "run.log"
        metadata_path = run_dir / "metadata.json"
        if not deck.is_file():
            raise RuntimeError(f"registered passive deck missing: {deck}")
        if raw.exists() or log.exists() or metadata_path.exists():
            raise RuntimeError(f"refusing to overwrite passive artifact: {run_dir}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("x", encoding="utf-8") as stream:
            completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
        finished = now()
        record: dict[str, Any] = {
            "schema": "bvm-population-passive-source-replay-run-metadata-v1",
            "experiment_id": EXP.name,
            "run_id": case,
            "phase": "passive_capture",
            "mask": MASKS[case],
            "hamming_weight": MASKS[case].count("1"),
            "started_at_local": started,
            "finished_at_local": finished,
            "git_head_before_run": current_head,
            "command": command,
            "solver": solver,
            "parameters": {"BVM_count": 4, "JSL_count": 8, "JSL_area": 5.0, "amplitude_uA": 100.0, "L1_pH": 1.4, "L2_pH": 2.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "IBias_uA": 260.0, "BJS_area": 4},
            "artifacts": {
                "deck": {"path": deck.relative_to(REPO).as_posix(), "sha256": sha256(deck), "bytes": deck.stat().st_size},
                "raw": {"path": raw.relative_to(REPO).as_posix(), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None},
                "log": {"path": log.relative_to(REPO).as_posix(), "sha256": sha256(log), "bytes": log.stat().st_size},
            },
            "exit_code": completed.returncode,
            "execution_status": "RUN_PASS" if completed.returncode == 0 and raw.is_file() else "RUN_FAIL",
            "physical_solve_this_experiment": True,
            "raw_immutable": True,
            "parameter_tuning": False,
            "scientific_analysis_performed": False,
            "raw_summary": raw_summary(raw),
        }
        metadata_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        records.append(record)
        if record["execution_status"] != "RUN_PASS":
            failures.append(case)
            break
    summary: dict[str, Any] = {
        "schema": "bvm-population-passive-source-replay-execution-v1",
        "experiment_id": EXP.name,
        "phase": "passive_capture",
        "started_at_local": records[0]["started_at_local"] if records else now(),
        "finished_at_local": now(),
        "head": current_head,
        "preflight_head": preflight.get("head_at_preflight"),
        "solver_solve_invocations": len(records),
        "exact_physical_solve_count": len(records),
        "authorized_physical_solve_count": 3,
        "authorized_total_experiment_solve_count": 6,
        "run_order": [record["run_id"] for record in records],
        "authorized_cases": list(CASES),
        "unauthorized_extra_solves": 0,
        "failed_runs": failures,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "no_retry_performed": True,
        "status": "PASS" if not failures and len(records) == len(CASES) else "FAIL",
        "runs": records,
    }
    output = EXP / "qa/execution_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise RuntimeError(f"refusing to overwrite execution summary: {output}")
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "solver_invocations": len(records), "authorized_passive_solves": 3, "failed_runs": failures, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
