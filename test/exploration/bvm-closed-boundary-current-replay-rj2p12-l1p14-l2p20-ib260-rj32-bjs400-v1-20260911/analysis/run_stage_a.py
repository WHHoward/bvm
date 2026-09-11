#!/usr/bin/env python3
"""Execute exactly the one authorized Stage A N2 replay solve."""

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
RUN_ID = "CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12"
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


def head_relation(preflight_head: str) -> dict[str, Any]:
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if current == preflight_head:
        return {"status": "PASS", "head": current, "relation": "EXACT"}
    changed = set(subprocess.check_output(["git", "diff", "--name-only", f"{preflight_head}..{current}"], cwd=REPO, text=True).splitlines())
    prefix = str(EXP.relative_to(REPO))
    allowed = {prefix + "/PREFLIGHT.md", prefix + "/analysis/preflight.json", prefix + "/analysis/STAGE_A_PREFLIGHT.md"}
    distance = int(subprocess.check_output(["git", "rev-list", "--count", f"{preflight_head}..{current}"], cwd=REPO, text=True).strip())
    valid = distance == 1 and changed == allowed
    return {"status": "PASS" if valid else "FAIL", "head": current, "relation": "PREFLIGHT_SEAL_COMMIT" if valid else "UNEXPECTED", "changed_paths": sorted(changed), "commit_distance": distance}


def main() -> int:
    preflight = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))
    if preflight.get("status") != "PASS" or preflight.get("authorized_current_turn_physical_solve_count") != 1 or preflight.get("physical_solve_count_before_preflight") != 0:
        raise RuntimeError("Stage A preflight is not a PASS one-solve gate")
    relation = head_relation(str(preflight["head_at_preflight"]))
    if relation["status"] != "PASS":
        raise RuntimeError(f"HEAD/preflight relation is not allowed: {relation}")
    if not SOLVER.is_file() or sha256(SOLVER) != SOLVER_SHA256:
        raise RuntimeError("solver identity changed")
    run_dir = EXP / "runs" / RUN_ID
    deck, raw, log, metadata_path = run_dir / "deck.cir", run_dir / "raw.csv", run_dir / "run.log", run_dir / "metadata.json"
    if not deck.is_file():
        raise RuntimeError(f"missing registered Stage A deck: {deck}")
    if raw.exists() or log.exists() or metadata_path.exists():
        raise RuntimeError("refusing to overwrite Stage A artifacts")
    source_manifest = json.loads((EXP / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    source_raw = EXP / "references/closed_loop_rj2p12" / "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011" / "raw.csv"
    command = [str(SOLVER), "-a", "1", "-o", str(raw), str(deck)]
    started = now()
    with log.open("x", encoding="utf-8") as stream:
        completed = subprocess.run(command, cwd=REPO, stdout=stream, stderr=subprocess.STDOUT, check=False)
    finished = now()
    record: dict[str, Any] = {
        "schema": "bvm-closed-boundary-current-replay-run-metadata-v1",
        "experiment_id": EXP.name,
        "run_id": RUN_ID,
        "stage": "A",
        "source_run": "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011",
        "source_signal": "I(B_JSL8)",
        "source_raw_sha256": sha256(source_raw),
        "working_point": {"L1_pH": 1.4, "L2_pH": 2.0, "RJ1_ohm": 32.0, "RJ2_ohm": 12.0, "IBias_uA": 260.0, "BJS_area": 4, "BJ1_area": 0.9, "BJ2_area": 2, "L3_pH": 1.3, "termination_ohm": 10.0},
        "started_at_local": started,
        "finished_at_local": finished,
        "git_head_before_run": relation["head"],
        "command": command,
        "solver": {"path": str(SOLVER.relative_to(REPO)), "sha256": sha256(SOLVER), "version": subprocess.check_output([str(SOLVER), "--version"], cwd=REPO, text=True)},
        "artifacts": {"deck": {"path": deck.relative_to(REPO).as_posix(), "sha256": sha256(deck), "bytes": deck.stat().st_size}, "raw": {"path": raw.relative_to(REPO).as_posix(), "exists": raw.is_file(), "sha256": sha256(raw) if raw.is_file() else None, "bytes": raw.stat().st_size if raw.is_file() else None}, "log": {"path": log.relative_to(REPO).as_posix(), "sha256": sha256(log), "bytes": log.stat().st_size}},
        "exit_code": completed.returncode,
        "execution_status": "RUN_PASS" if completed.returncode == 0 and raw.is_file() else "RUN_FAIL",
        "physical_solve_this_experiment": True,
        "raw_immutable": True,
        "parameter_tuning": False,
        "scientific_analysis_performed": False,
        "raw_summary": raw_summary(raw),
        "stage_b_started": False,
        "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json"),
    }
    metadata_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary: dict[str, Any] = {"schema": "bvm-closed-boundary-current-replay-execution-v1", "experiment_id": EXP.name, "stage": "A", "started_at_local": started, "finished_at_local": finished, "head": relation["head"], "preflight_head": preflight["head_at_preflight"], "solver_solve_invocations": 1, "exact_physical_solve_count": 1, "authorized_current_turn_physical_solve_count": 1, "maximum_task_physical_solve_count": 2, "run_order": [RUN_ID], "authorized_cases": [RUN_ID], "stage_b_started": False, "stage_b_status": "DEFERRED_PENDING_SCIENTIFIC_REVIEW_AUTHORIZATION", "unauthorized_extra_solves": 0, "failed_runs": [] if record["execution_status"] == "RUN_PASS" else [RUN_ID], "raw_files_modified": 0, "scientific_analysis_performed": False, "no_retry_performed": True, "status": "PASS" if record["execution_status"] == "RUN_PASS" else "FAIL", "run": record, "source_manifest_sha256": sha256(EXP / "SOURCE_MANIFEST.json")}
    output = EXP / "qa/execution_summary.json"
    if output.exists():
        raise RuntimeError(f"refusing to overwrite execution summary: {output}")
    output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": summary["status"], "solver_invocations": 1, "stage_b_started": False, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
