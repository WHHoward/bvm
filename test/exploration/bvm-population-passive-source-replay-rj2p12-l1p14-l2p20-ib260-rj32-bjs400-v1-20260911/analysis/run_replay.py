#!/usr/bin/env python3
"""Execute exactly the three registered RJ2=12 replay solves."""

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
CASES = ("REPLAY_N2_0011_RJ2P12", "REPLAY_N3_0111_RJ2P12", "REPLAY_N4_1111_RJ2P12")
SOURCE_CASE = {"REPLAY_N2_0011_RJ2P12": "PASSIVE_N2_0011", "REPLAY_N3_0111_RJ2P12": "PASSIVE_N3_0111", "REPLAY_N4_1111_RJ2P12": "PASSIVE_N4_1111"}
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


def preflight_head_relation(preflight_head: str) -> dict[str, Any]:
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if current == preflight_head:
        return {"status": "PASS", "head": current, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{current}"], cwd=REPO, text=True).splitlines())
    prefix = str(EXP.relative_to(REPO))
    allowed = {prefix + "/analysis/REPLAY_PREFLIGHT.md", prefix + "/qa/replay_fidelity_qa.json", prefix + "/qa/replay_preflight.json"}
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{current}"], cwd=REPO, text=True).strip())
    valid = distance == 1 and changed == allowed
    return {"status": "PASS" if valid else "FAIL", "head": current, "relation": "REPLAY_PREFLIGHT_SEAL_COMMIT" if valid else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def main() -> int:
    preflight = json.loads((EXP / "qa/replay_preflight.json").read_text(encoding="utf-8"))
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or preflight.get("authorized_replay_solve_count") != 3 or preflight.get("physical_solve_count_before_replay") != 3:
        raise RuntimeError("replay execution gate is not a PASS three-solve preflight")
    if execution.get("status") != "PASS" or execution.get("exact_physical_solve_count") != 3:
        raise RuntimeError("passive execution prefix is not PASS")
    relation = preflight_head_relation(str(preflight.get("head_at_replay_preflight")))
    if relation["status"] != "PASS":
        raise RuntimeError(f"HEAD/replay-preflight relation is not allowed: {relation}")
    current_head = relation["head"]
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("registered solver identity changed")
    solver = {"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for case in CASES:
        run_dir = EXP / "runs" / case
        deck, raw, log, metadata_path = run_dir / "deck.cir", run_dir / "raw.csv", run_dir / "run.log", run_dir / "metadata.json"
        if not deck.is_file():
            raise RuntimeError(f"registered replay deck missing: {deck}")
        if raw.exists() or log.exists() or metadata_path.exists():
            raise RuntimeError(f"refusing to overwrite replay artifact: {run_dir}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("x", encoding="utf-8") as stream:
            completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
        finished = now()
        record: dict[str, Any] = {
            "schema": "bvm-population-passive-source-replay-run-metadata-v1",
            "experiment_id": EXP.name,
            "run_id": case,
            "phase": "exact_current_replay",
            "source_case": SOURCE_CASE[case],
            "working_point": {"L1_pH": 1.4, "L2_pH": 2.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "IBias_uA": 260.0, "BJS_area": 4, "termination_ohm": 10.0},
            "started_at_local": started,
            "finished_at_local": finished,
            "git_head_before_run": current_head,
            "command": command,
            "solver": solver,
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
        "schema": "bvm-population-passive-source-replay-replay-execution-v1",
        "experiment_id": EXP.name,
        "phase": "exact_current_replay",
        "started_at_local": records[0]["started_at_local"] if records else now(),
        "finished_at_local": now(),
        "head": current_head,
        "replay_preflight_head": preflight.get("head_at_replay_preflight"),
        "passive_solve_count": 3,
        "solver_solve_invocations": len(records),
        "exact_physical_solve_count": len(records),
        "authorized_replay_solve_count": 3,
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
    output = EXP / "qa/replay_execution_summary.json"
    if output.exists():
        raise RuntimeError(f"refusing to overwrite replay execution summary: {output}")
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    combined = dict(summary)
    combined["schema"] = "bvm-population-passive-source-replay-combined-execution-v1"
    combined["passive_execution_summary"] = "qa/execution_summary.json"
    combined["replay_execution_summary"] = "qa/replay_execution_summary.json"
    combined["total_solver_solve_invocations"] = 3 + len(records)
    combined["total_authorized_physical_solve_count"] = 6
    combined["exact_total_physical_solve_count"] = 3 + len(records)
    combined["status"] = "PASS" if summary["status"] == "PASS" else "FAIL"
    combined_path = EXP / "qa/execution_summary_combined.json"
    combined_path.write_text(json.dumps(combined, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "solver_invocations": len(records), "authorized_replay_solves": 3, "total_experiment_solves": 3 + len(records), "failed_runs": failures, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
