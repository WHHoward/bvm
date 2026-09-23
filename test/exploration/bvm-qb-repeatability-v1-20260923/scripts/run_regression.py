#!/usr/bin/env python3
"""Run only the five registered A–E platform regression cases."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from common import REGRESSION_MATRIX, ROOT, read_json, repo_rel, sha256, write_json
from preflight import build_gate


def run_tree_hashes(run_dir: Path) -> dict[str, str]:
    return {repo_rel(path): sha256(path) for path in sorted(run_dir.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute the exact five-case A–E matrix once")
    parser.add_argument("--dry-run", action="store_true", help="show exact cases without creating runs or solving")
    args = parser.parse_args()
    gate = build_gate(require_clean=not args.dry_run)
    if args.dry_run:
        print(json.dumps({"preflight_status": gate["status"], "authorized_solve_count": gate["authorized_solve_count"],
                          "cases": [{"case_id": item["case_id"], "parameters": item["parameters"],
                                     "read_schedule": item["schedule"], "stop_ps": item["stop_ps"]}
                                    for item in gate["cases"]], "no_solve_executed": True},
                         ensure_ascii=False, indent=2))
        return 0 if gate["status"] == "PASS" else 2
    if gate["status"] != "PASS":
        write_json(ROOT / "analysis" / "PREFLIGHT_QA.json", gate)
        print(json.dumps(gate, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    write_json(ROOT / "analysis" / "PREFLIGHT_QA.json", gate)
    receipts_dir = ROOT / "analysis" / "receipts"
    execution_path = ROOT / "analysis" / "REGRESSION_EXECUTION.json"
    if execution_path.exists() or (receipts_dir.exists() and any(receipts_dir.iterdir())):
        raise RuntimeError("registered regression execution/receipt evidence already exists; refusing restart/overwrite")
    matrix = read_json(REGRESSION_MATRIX)
    execution = {"schema": "bvm-qb-repeatability-regression-execution-v1",
                 "preflight_status": "PASS", "preflight_head": gate["git"]["head"],
                 "preflight_qa_sha256": sha256(ROOT / "analysis" / "PREFLIGHT_QA.json"),
                 "authorized_solve_count": int(matrix["authorized_solve_count"]),
                 "completed_solve_count": 0, "automatic_retry": False,
                 "scientific_interpretation_performed": False, "runs": []}
    write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
    for case in matrix["cases"]:
        command = [sys.executable, str(ROOT / "scripts" / "run_case.py"),
                   "--registered-case", case["case_id"]]
        overrides = {"NAME": case["case_id"], **{str(k): str(v) for k, v in case["overrides"].items()}}
        for key, value in overrides.items():
            command.extend(("--set", f"{key}={value}"))
        if case.get("reference_run"):
            command.extend(("--reference-run", case["reference_run"]))
        print(f"\n=== {case['case_id']} ({case['purpose']}) ===", flush=True)
        completed = subprocess.run(command, cwd=ROOT.parents[2], check=False)
        run_dir = ROOT / "runs" / case["case_id"]
        metadata_path, result_path = run_dir / "metadata.json", run_dir / "result.json"
        metadata = read_json(metadata_path) if metadata_path.is_file() else {}
        result = read_json(result_path) if result_path.is_file() else {}
        artifact_paths = {"metadata": metadata_path, "result": result_path,
                          "raw": run_dir / "raw.csv", "deck": run_dir / "actual_deck.cir",
                          "stimulus": run_dir / "stimulus.inc", "config_snapshot": run_dir / "config_snapshot.env",
                          "stimulus_snapshot": run_dir / "stimulus_snapshot.json",
                          "source_manifest": run_dir / "source_manifest.json"}
        artifact_hashes = {key: sha256(path) if path.is_file() else None for key, path in artifact_paths.items()}
        receipt = {"schema": "bvm-qb-repeatability-independent-run-receipt-v1",
                   "case_id": case["case_id"], "purpose": case["purpose"],
                   "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
                   "preflight_head": gate["git"]["head"],
                   "preflight_qa_sha256": execution["preflight_qa_sha256"],
                   "runner_command": command, "runner_exit_code": completed.returncode,
                   "run_dir": str(run_dir.relative_to(ROOT.parents[2])),
                   "execution_status": metadata.get("execution_status", "RUN_NOT_STARTED"),
                   "artifact_status": result.get("artifact_status", "MISSING"),
                   "physical_solve_count": int(metadata.get("physical_solve_count", 0)),
                   "parameters": metadata.get("parameters"), "solver": metadata.get("solver"),
                   "artifact_sha256": artifact_hashes,
                   "run_tree_file_sha256": run_tree_hashes(run_dir) if run_dir.is_dir() else {},
                   "scientific_interpretation_performed": False, "automatic_follow_up": False}
        receipt_path = receipts_dir / f"{case['case_id']}.json"
        receipts_dir.mkdir(parents=True, exist_ok=True)
        with receipt_path.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        execution["runs"].append({"case_id": case["case_id"], "command": command,
                                  "exit_code": completed.returncode,
                                  "receipt_path": str(receipt_path.relative_to(ROOT.parents[2])),
                                  "receipt_sha256": sha256(receipt_path),
                                  "physical_solve_count": receipt["physical_solve_count"],
                                  "raw_sha256": artifact_hashes["raw"],
                                  "status": "COMPLETE" if completed.returncode == 0 else "STOPPED_ON_FAILURE"})
        if completed.returncode != 0:
            execution["status"] = "STOPPED_ON_FAILURE"
            write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
            print("Stopped at first failed case; no retry and no later case was run.", file=sys.stderr)
            return completed.returncode or 2
        execution["completed_solve_count"] += 1
        write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
    execution["status"] = "ALL_REGISTERED_RUNS_COMPLETE"
    write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
    final = subprocess.run([sys.executable, str(ROOT / "scripts" / "finalize.py")],
                           cwd=ROOT.parents[2], check=False)
    return final.returncode


if __name__ == "__main__":
    raise SystemExit(main())
