#!/usr/bin/env python3
"""Execute exactly the one authorized RJ2=10/0111 solve."""

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
RUN_ID = "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111"


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
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if current == preflight_head:
        return {"status": "PASS", "head": current, "preflight_head": preflight_head, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{current}"], cwd=REPO, text=True).splitlines())
    prefix = str(EXP.relative_to(REPO)).rstrip("/")
    allowed = {prefix + "/PREFLIGHT.md", prefix + "/analysis/preflight.json"}
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{current}"], cwd=REPO, text=True).strip())
    valid = distance == 1 and changed == allowed
    return {"status": "PASS" if valid else "FAIL", "head": current, "preflight_head": preflight_head, "relation": "PREFLIGHT_ONLY_SEAL_COMMIT" if valid else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def main() -> int:
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    regression = json.loads((EXP / "qa/oracle_regression.json").read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or preflight.get("new_physical_solve_count") != 1 or preflight.get("reference_case_count") != 6:
        raise RuntimeError("diagnostic preflight is not PASS for exactly one new solve")
    if regression.get("status") != "PASS" or regression.get("marker") != "ORACLE_REGRESSION_PASS" or regression.get("physical_solve_count") != 0:
        raise RuntimeError("oracle regression did not PASS before solve")
    relation = head_relation(str(preflight["head"]))
    if relation["status"] != "PASS":
        raise RuntimeError(f"HEAD/preflight relation is not allowed: {relation}")
    if not SOLVER.is_file() or sha256(SOLVER) != "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2":
        raise RuntimeError("solver identity mismatch")
    run_dir = EXP / "runs" / RUN_ID
    deck, raw, log, meta = run_dir / "deck.cir", run_dir / "raw.csv", run_dir / "run.log", run_dir / "metadata.json"
    if not deck.is_file():
        raise RuntimeError(f"missing registered deck: {deck}")
    if raw.exists() or log.exists() or meta.exists():
        raise RuntimeError(f"refusing to overwrite new artifact: {run_dir}")
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    with log.open("w", encoding="utf-8") as stream:
        completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
    finished = now()
    record = {"schema": "bjs400-rj2p10-weight3-run-metadata-v1", "experiment_id": EXP.name, "run_id": RUN_ID, "topology": "ARRAY", "working_point": {"L1_pH": 1.4, "L2_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "RJ2_ohm": 10.0}, "mask": "0111", "hamming_weight": 3, "parameters": {"L1_pH": 1.4, "L2_pH": 2.0, "IBias_uA": 260.0, "RJ1_ohm": 32.0, "RJ2_ohm": 10.0, "mask": "0111"}, "started_at_local": started, "finished_at_local": finished, "git_head_before_run": relation["head"], "command": command, "solver": {"path": str(SOLVER), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)}, "artifacts": {"deck": {"path": str(deck), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "raw": {"path": str(raw), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}, "log": {"path": str(log), "sha256": sha256(log), "bytes": log.stat().st_size}}, "exit_code": completed.returncode, "execution_status": "RUN_PASS" if completed.returncode == 0 and raw.is_file() else "RUN_FAIL", "physical_solve_this_experiment": True, "raw_immutable": True, "parameter_tuning": False, "scientific_analysis_performed": False, "raw_summary": raw_summary(raw)}
    meta.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {"schema": "bjs400-rj2p10-weight3-execution-v1", "experiment_id": EXP.name, "started_at_local": started, "finished_at_local": finished, "head": relation["head"], "preflight_head": preflight["head"], "solver_solve_invocations": 1, "exact_new_physical_solve_count": 1, "authorized_new_physical_solve_count": 1, "reference_case_count": 6, "unauthorized_extra_solves": 0, "failed_runs": [] if record["execution_status"] == "RUN_PASS" else [RUN_ID], "run_order": [RUN_ID], "authorized_run_id": RUN_ID, "authorized_mask": "0111", "reference_cases": ["RJ2P10_0001", "RJ2P10_0011", "RJ2P11_0011", "RJ2P11_0111", "RJ2P12_0011", "RJ2P12_0111"], "raw_files_modified": 0, "scientific_interpretation_performed": False, "no_retry_performed": True, "status": "PASS" if record["execution_status"] == "RUN_PASS" else "FAIL", "run": record}
    (EXP / "qa").mkdir(parents=True, exist_ok=True)
    (EXP / "qa/execution_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "solver_invocations": 1, "new_physical_solve_count": 1, "authorized_run_id": RUN_ID, "failed_runs": summary["failed_runs"], "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
