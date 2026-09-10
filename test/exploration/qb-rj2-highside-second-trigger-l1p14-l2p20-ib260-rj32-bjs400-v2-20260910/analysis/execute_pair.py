#!/usr/bin/env python3
"""Execute exactly one registered RJ2 pair for the next protocol stage.

The next pair is intentionally not selected from a solver result.  A separate
stage decision, made after mechanical QA, must record ``CONTINUE`` before the
following pair can be executed.
"""

from __future__ import annotations

import argparse
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
from prepare_experiment import FIXED, NEW_RUNS, REUSE_RUNS, RJ2_VALUES, RUN_TO_MASK, RUN_TO_RJ2  # noqa: E402


REGISTERED_NEW_RUNS = tuple(NEW_RUNS)
STAGES = {
    1: REGISTERED_NEW_RUNS[0:2],
    2: REGISTERED_NEW_RUNS[2:4],
    3: REGISTERED_NEW_RUNS[4:6],
}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def solver_version() -> str:
    return subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)


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


def head_relation(preflight_head: str) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head == preflight_head:
        return {"status": "PASS", "head": head, "preflight_head": preflight_head, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{head}"], cwd=REPO, text=True).splitlines())
    allowed = {str(EXP.relative_to(REPO) / "PREFLIGHT.md"), str(EXP.relative_to(REPO) / "analysis/preflight.json")}
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{head}"], cwd=REPO, text=True).strip())
    valid = distance == 1 and changed == allowed
    return {"status": "PASS" if valid else "FAIL", "head": head, "preflight_head": preflight_head, "relation": "PREFLIGHT_ONLY_SEAL_COMMIT" if valid else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def make_record(run_id: str, head: str, command: list[str], started: str, finished: str, exit_code: int, deck: Path, raw: Path, log: Path) -> dict[str, Any]:
    rj2 = RUN_TO_RJ2[run_id]
    return {
        "schema": "bjs400-rj2-highside-second-trigger-run-metadata-v2",
        "experiment_id": EXP.name,
        "run_id": run_id,
        "topology": "ARRAY",
        "working_point": {"L1_pH": FIXED["L1_pH"], "L2_pH": FIXED["L2_pH"], "IBias_uA": FIXED["IBias_uA"], "RJ1_ohm": FIXED["RJ1_ohm"], "RJ2_ohm": rj2},
        "rj2_ohm": rj2,
        "mask": RUN_TO_MASK[run_id],
        "parameters": {**FIXED, "RJ2_ohm": rj2},
        "started_at_local": started,
        "finished_at_local": finished,
        "git_head_before_run": head,
        "command": command,
        "solver": {"path": str(SOLVER), "sha256": sha256(SOLVER), "version": solver_version()},
        "artifacts": {
            "deck": {"path": str(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size},
            "raw": {"path": str(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None},
            "log": {"path": str(log), "sha256": sha256(log), "bytes": log.stat().st_size},
        },
        "exit_code": exit_code,
        "execution_status": "RUN_PASS" if exit_code == 0 and raw.is_file() else "RUN_FAIL",
        "physical_solve_this_experiment": True,
        "raw_immutable": True,
        "parameter_tuning": False,
        "scientific_analysis_performed": False,
        "raw_summary": raw_summary(raw),
    }


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, choices=sorted(STAGES), required=True)
    args = parser.parse_args()
    stage = args.stage
    preflight = load_json(EXP / "analysis/preflight.json")
    if preflight.get("status") != "PASS" or preflight.get("new_physical_solve_count") != 6 or preflight.get("reused_physical_case_count") != 2:
        raise RuntimeError("preflight is not PASS for the registered 6-new/2-reuse matrix")
    relation = head_relation(str(preflight["head"]))
    if relation["status"] != "PASS":
        raise RuntimeError(f"HEAD/preflight relation is not allowed: {relation}")
    if not SOLVER.is_file():
        raise RuntimeError(f"missing solver: {SOLVER}")

    summary_path = EXP / "qa/execution_summary.json"
    if summary_path.is_file():
        summary = load_json(summary_path)
    else:
        summary = {
            "schema": "bjs400-rj2-highside-second-trigger-execution-v2",
            "experiment_id": EXP.name,
            "started_at_local": now(),
            "head": relation["head"],
            "preflight_head": preflight["head"],
            "solver_solve_invocations": 0,
            "exact_new_physical_solve_count": 0,
            "authorized_new_physical_solve_max": 6,
            "reused_physical_case_count": 2,
            "unauthorized_extra_solves": 0,
            "failed_runs": [],
            "run_order": [],
            "reused_cases": list(REUSE_RUNS),
            "new_rj2_values_ohm": list(RJ2_VALUES),
            "runs": [],
            "stage_records": [],
            "stage_decisions": [],
            "raw_files_modified": 0,
            "scientific_analysis_performed": False,
            "no_retry_performed": True,
            "early_stop_reason": None,
            "registered_unrun_values": list(REGISTERED_NEW_RUNS),
            "status": "PASS",
        }
    if summary.get("early_stop_reason") is not None:
        raise RuntimeError("a previous stage already recorded STOP; no successor stage is authorized")
    previous_order = tuple(summary.get("run_order", ()))
    expected_prefix = REGISTERED_NEW_RUNS[: 2 * (stage - 1)]
    if previous_order != expected_prefix:
        raise RuntimeError(f"stage {stage} requires previous completed prefix {expected_prefix}, found {previous_order}")
    decisions = summary.get("stage_decisions", [])
    if len(decisions) != stage - 1 or any(item.get("decision") != "CONTINUE" for item in decisions):
        raise RuntimeError(f"stage {stage} requires CONTINUE decisions for all prior stages")
    pair = STAGES[stage]
    executed: list[str] = []
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    head = relation["head"]
    stage_started = now()
    for run_id in pair:
        run_dir = EXP / "runs" / run_id
        deck = run_dir / "deck.cir"
        raw = run_dir / "raw.csv"
        log = run_dir / "run.log"
        metadata = run_dir / "metadata.json"
        if not deck.is_file():
            raise RuntimeError(f"missing registered deck: {deck}")
        if raw.exists() or log.exists() or metadata.exists():
            raise RuntimeError(f"refusing to overwrite new run artifact: {run_dir}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("w", encoding="utf-8") as stream:
            completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
        finished = now()
        record = make_record(run_id, head, command, started, finished, completed.returncode, deck, raw, log)
        metadata.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        records.append(record)
        executed.append(run_id)
        if record["execution_status"] != "RUN_PASS":
            failures.append(run_id)
            break

    cumulative_order = list(previous_order) + executed
    all_records = list(summary.get("runs", [])) + records
    stage_record = {
        "stage": stage,
        "rj2_ohm": RUN_TO_RJ2[pair[0]],
        "registered_pair": list(pair),
        "executed_runs": executed,
        "stage_started_at_local": stage_started,
        "stage_finished_at_local": now(),
        "execution_status": "PASS" if not failures and tuple(executed) == pair else "FAIL",
        "failed_runs": failures,
        "scientific_analysis_performed": False,
    }
    summary.update({
        "schema": "bjs400-rj2-highside-second-trigger-execution-v2",
        "experiment_id": EXP.name,
        "finished_at_local": now(),
        "head": head,
        "preflight_head": preflight["head"],
        "solver_solve_invocations": len(cumulative_order),
        "exact_new_physical_solve_count": len(cumulative_order),
        "authorized_new_physical_solve_max": 6,
        "reused_physical_case_count": 2,
        "unauthorized_extra_solves": 0,
        "failed_runs": list(summary.get("failed_runs", [])) + failures,
        "run_order": cumulative_order,
        "reused_cases": list(REUSE_RUNS),
        "new_rj2_values_ohm": list(RJ2_VALUES),
        "runs": all_records,
        "stage_records": list(summary.get("stage_records", [])) + [stage_record],
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "no_retry_performed": True,
        "early_stop_rule": "after each complete RJ2 pair, mechanical QA and stage_decision.py must record CONTINUE before the next pair; STOP on control, first-response/0001, second-response candidate or protocol failure",
        "early_stop_reason": None,
        "registered_unrun_values": [run_id for run_id in REGISTERED_NEW_RUNS if run_id not in cumulative_order],
        "status": "PASS" if not failures else "FAIL",
    })
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "stage": stage, "stage_runs": executed, "solver_invocations": len(cumulative_order), "new_physical_solve_count": len(cumulative_order), "failed_runs": failures, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
