#!/usr/bin/env python3
"""Execute the registered high-L2 runs in ascending order once.

The runner stops before a later L2 value if the registered mechanical
multi-evidence criterion observes a second downstream progression candidate
after the first FINAL-origin BJ2 +0.9 navigation anchor.  L1 re-crossing alone
never stops this experiment.
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
from prepare_experiment import FIXED, L2_VALUES, NEW_RUNS, REUSE_RUNS, RUN_TO_L2, RUN_TO_MASK  # noqa: E402


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
    return {
        "header_count": len(header),
        "sample_count": count,
        "first_timestamp": first[0],
        "last_timestamp": last[0],
    }


def observed_second_complete_candidate(raw: Path) -> bool:
    """Apply only the registered post-anchor multi-evidence stop criterion."""
    if not raw.is_file():
        return False
    with raw.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    columns = {name: [] for name in header}
    for row in rows:
        for name, value in zip(header, row):
            columns[name].append(float(value))
    times = columns["time"]
    phase = columns["P(BJ2|XBQ1)"]
    def first_anchor(label: str, threshold: float, baseline_index: int, start_index: int) -> int | None:
        values = columns[label]
        continuous = [values[0]]
        for current, previous in zip(values[1:], values):
            delta = current - previous
            while delta > 3.141592653589793:
                delta -= 2.0 * 3.141592653589793
            while delta < -3.141592653589793:
                delta += 2.0 * 3.141592653589793
            continuous.append(continuous[-1] + delta)
        reference = continuous[baseline_index]
        return next((index for index in range(start_index, len(times)) if times[index] < 200e-12 and (continuous[index] - reference) / (2.0 * 3.141592653589793) >= threshold), None)
    continuous = [phase[0]]
    for current, previous in zip(phase[1:], phase):
        delta = current - previous
        while delta > 3.141592653589793:
            delta -= 2.0 * 3.141592653589793
        while delta < -3.141592653589793:
            delta += 2.0 * 3.141592653589793
        continuous.append(continuous[-1] + delta)
    baseline = next(index for index, value in enumerate(times) if 101e-12 <= value < 110e-12)
    anchor = next((index for index, value in enumerate(times) if 110e-12 <= value < 200e-12 and (continuous[index] - continuous[baseline]) / (2.0 * 3.141592653589793) >= 0.9), None)
    if anchor is None:
        return False
    bj1_second = first_anchor("P(BJ1|XBQ1)", 0.5, anchor, anchor)
    bj2_second = first_anchor("P(BJ2|XBQ1)", 0.5, anchor, anchor)
    jtl_times = []
    for stage in range(1, 7):
        jtl_times.append(first_anchor(f"P(B01|XJTL1_{stage})", 0.5, anchor, anchor))
    ordered = all(value is not None for value in jtl_times) and all(jtl_times[index] < jtl_times[index + 1] for index in range(5))
    qbout = columns["V(QBOUT)"]
    terminal = columns["V(JTL6_OUT)"]
    post_indexes = [index for index, value in enumerate(times) if times[anchor] <= value < 200e-12]
    return bj1_second is not None and bj2_second is not None and ordered and any(abs(qbout[index]) > 0.0 for index in post_indexes) and any(abs(terminal[index]) > 0.0 for index in post_indexes)


def head_relation(preflight_head: str) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head == preflight_head:
        return {"status": "PASS", "head": head, "preflight_head": preflight_head, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{head}"], cwd=REPO, text=True).splitlines())
    allowed = {
        str(EXP.relative_to(REPO) / "PREFLIGHT.md"),
        str(EXP.relative_to(REPO) / "analysis/preflight.json"),
    }
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{head}"], cwd=REPO, text=True).strip())
    status = "PASS" if distance == 1 and changed == allowed else "FAIL"
    return {"status": status, "head": head, "preflight_head": preflight_head, "relation": "PREFLIGHT_ONLY_SEAL_COMMIT" if status == "PASS" else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def make_record(run_id: str, head: str, command: list[str], started: str, finished: str, exit_code: int, deck: Path, raw: Path, log: Path) -> dict[str, Any]:
    return {
        "schema": "bjs400-l2-highside-second-trigger-run-metadata-v1",
        "experiment_id": EXP.name,
        "run_id": run_id,
        "topology": "ARRAY",
        "working_point": {"L1_pH": FIXED["L1_pH"], "L2_pH": RUN_TO_L2[run_id], "IBias_uA": FIXED["IBias_uA"], "RJ1_ohm": FIXED["RJ1_ohm"], "RJ2_ohm": FIXED["RJ2_ohm"]},
        "l2_pH": RUN_TO_L2[run_id],
        "rj2_ohm": FIXED["RJ2_ohm"],
        "mask": RUN_TO_MASK[run_id],
        "parameters": {**FIXED, "L2_pH": RUN_TO_L2[run_id]},
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
        "physical_solve_this_experiment": True,
        "raw_immutable": True,
        "parameter_tuning": False,
        "scientific_analysis_performed": False,
        "raw_summary": raw_summary(raw),
    }


def main() -> int:
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or preflight.get("new_physical_solve_count") != 6 or preflight.get("reused_physical_case_count") != 2:
        raise RuntimeError("preflight is not PASS for exact 6-new/2-reuse matrix")
    relation = head_relation(str(preflight["head"]))
    if relation["status"] != "PASS":
        raise RuntimeError(f"HEAD/preflight relation is not allowed: {relation}")
    if not SOLVER.is_file():
        raise RuntimeError(f"missing solver: {SOLVER}")
    head = relation["head"]
    started_all = now()
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    executed_run_ids: list[str] = []
    stop_reason: str | None = None
    for run_id in NEW_RUNS:
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
        executed_run_ids.append(run_id)
        if record["execution_status"] != "RUN_PASS":
            failures.append(run_id)
            break
        if run_id.endswith("_0011") and observed_second_complete_candidate(raw):
            stop_reason = f"SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE:{run_id}"
            break
    summary = {
        "schema": "bjs400-l2-highside-second-trigger-execution-v1",
        "experiment_id": EXP.name,
        "started_at_local": started_all,
        "finished_at_local": now(),
        "head": head,
        "preflight_head": preflight["head"],
        "solver_solve_invocations": len(executed_run_ids),
        "exact_new_physical_solve_count": len(executed_run_ids),
        "authorized_new_physical_solve_max": 6,
        "reused_physical_case_count": 2,
        "unauthorized_extra_solves": 0,
        "failed_runs": failures,
        "run_order": executed_run_ids,
        "reused_cases": list(REUSE_RUNS),
        "new_l2_values_pH": list(L2_VALUES),
        "runs": records,
        "raw_files_modified": 0,
        "scientific_analysis_performed": False,
        "no_retry_performed": True,
        "early_stop_rule": "stop after a completed L2 pair if a strict second BJ1/BJ2/QBOUT/ordered-JTL/terminal multi-evidence candidate is observed; L1 re-crossing alone does not stop",
        "early_stop_reason": stop_reason,
        "registered_unrun_values": [run_id for run_id in NEW_RUNS if run_id not in executed_run_ids],
        "status": "PASS" if not failures else "FAIL",
    }
    output = EXP / "qa/execution_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": summary["status"],
        "solver_invocations": len(executed_run_ids),
        "new_physical_solve_count": len(executed_run_ids),
        "reused_physical_case_count": 2,
        "failed_runs": failures,
        "scientific_analysis_performed": False,
    }, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
