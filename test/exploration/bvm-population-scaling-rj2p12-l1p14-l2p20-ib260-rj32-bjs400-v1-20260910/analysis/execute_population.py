#!/usr/bin/env python3
"""Execute exactly the five registered new BVM mask cases."""

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
from prepare_population import AUTH, FIXED, NEW_MASKS, NEW_RUNS, REUSE_RUNS, RUN_TO_MASK  # noqa: E402


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


def head_relation(preflight_head: str) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if head == preflight_head:
        return {"status": "PASS", "head": head, "preflight_head": preflight_head, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{head}"], cwd=REPO, text=True).splitlines())
    prefix = str(EXP.relative_to(REPO)).rstrip("/")
    allowed = {prefix + "/PREFLIGHT.md", prefix + "/analysis/preflight.json"}
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{head}"], cwd=REPO, text=True).strip())
    valid = distance == 1 and changed == allowed
    return {"status": "PASS" if valid else "FAIL", "head": head, "preflight_head": preflight_head, "relation": "PREFLIGHT_ONLY_SEAL_COMMIT" if valid else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def metadata(run_id: str, head: str, command: list[str], started: str, finished: str, exit_code: int, deck: Path, raw: Path, log: Path) -> dict[str, Any]:
    mask = RUN_TO_MASK[run_id]
    return {"schema": "bjs400-population-mask-run-metadata-v1", "experiment_id": EXP.name, "run_id": run_id, "topology": "ARRAY", "working_point": FIXED, "mask": mask, "hamming_weight": mask.count("1"), "parameters": {**FIXED, "mask": mask}, "started_at_local": started, "finished_at_local": finished, "git_head_before_run": head, "command": command, "solver": {"path": str(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "artifacts": {"deck": {"path": str(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "raw": {"path": str(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}, "log": {"path": str(log), "sha256": sha256(log), "bytes": log.stat().st_size}}, "exit_code": exit_code, "execution_status": "RUN_PASS" if exit_code == 0 and raw.is_file() else "RUN_FAIL", "physical_solve_this_experiment": True, "raw_immutable": True, "parameter_tuning": False, "scientific_analysis_performed": False, "raw_summary": raw_summary(raw)}


def main() -> int:
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    regression = json.loads((EXP / "qa/oracle_regression.json").read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or preflight.get("new_physical_solve_count") != 5 or preflight.get("reused_physical_case_count") != 2:
        raise RuntimeError("population preflight is not PASS for 5-new/2-reuse matrix")
    if regression.get("status") != "PASS" or regression.get("marker") != "ORACLE_REGRESSION_PASS" or regression.get("physical_solve_count") != 0:
        raise RuntimeError("generalized oracle regression did not PASS before new runs")
    relation = head_relation(str(preflight["head"]))
    if relation["status"] != "PASS":
        raise RuntimeError(f"HEAD/preflight relation is not allowed: {relation}")
    if not SOLVER.is_file():
        raise RuntimeError(f"missing solver: {SOLVER}")
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for run_id in NEW_RUNS:
        run_dir = EXP / "runs" / run_id
        deck, raw, log, meta = run_dir / "deck.cir", run_dir / "raw.csv", run_dir / "run.log", run_dir / "metadata.json"
        if not deck.is_file():
            raise RuntimeError(f"missing registered deck: {deck}")
        if raw.exists() or log.exists() or meta.exists():
            raise RuntimeError(f"refusing to overwrite new mask artifact: {run_dir}")
        command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
        started = now()
        with log.open("w", encoding="utf-8") as stream:
            completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
        finished = now()
        record = metadata(run_id, relation["head"], command, started, finished, completed.returncode, deck, raw, log)
        meta.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        records.append(record)
        if record["execution_status"] != "RUN_PASS":
            failures.append(run_id)
            break
    summary = {"schema": "bjs400-population-mask-execution-v1", "experiment_id": EXP.name, "started_at_local": records[0]["started_at_local"] if records else now(), "finished_at_local": now(), "head": relation["head"], "preflight_head": preflight["head"], "solver_solve_invocations": len(records), "exact_new_physical_solve_count": len(records), "authorized_new_physical_solve_count": 5, "reused_physical_case_count": 2, "logical_case_count": 7, "unauthorized_extra_solves": 0, "failed_runs": failures, "run_order": [record["run_id"] for record in records], "reused_cases": list(REUSE_RUNS), "new_masks": list(NEW_MASKS), "runs": records, "raw_files_modified": 0, "scientific_analysis_performed": False, "no_retry_performed": True, "status": "PASS" if not failures and len(records) == 5 else "FAIL"}
    output = EXP / "qa/execution_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "solver_invocations": len(records), "new_physical_solve_count": len(records), "reused_physical_case_count": 2, "new_masks": list(NEW_MASKS), "failed_runs": failures, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
