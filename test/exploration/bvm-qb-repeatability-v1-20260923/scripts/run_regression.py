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


def run_artifact_paths(run_dir: Path) -> dict[str, Path]:
    return {"metadata": run_dir / "metadata.json", "result": run_dir / "result.json",
            "raw": run_dir / "raw.csv", "deck": run_dir / "actual_deck.cir",
            "stimulus": run_dir / "stimulus.inc", "config_snapshot": run_dir / "config_snapshot.env",
            "stimulus_snapshot": run_dir / "stimulus_snapshot.json",
            "source_manifest": run_dir / "source_manifest.json",
            "stdout": run_dir / "stdout.txt", "stderr": run_dir / "stderr.txt",
            "run_log": run_dir / "run.log"}


def artifact_hashes(run_dir: Path) -> dict[str, str | None]:
    return {key: sha256(path) if path.is_file() else None
            for key, path in run_artifact_paths(run_dir).items()}


def write_exclusive_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def archive_previous_attempt() -> dict[str, dict[str, str]]:
    attempt_dir = ROOT / "analysis" / "attempts" / "PLATFORM_ATTEMPT1"
    attempt_dir.mkdir(parents=True, exist_ok=False)
    sources = {
        "PREFLIGHT_QA.json": ROOT / "analysis" / "PREFLIGHT_QA.json",
        "REGRESSION_EXECUTION.json": ROOT / "analysis" / "REGRESSION_EXECUTION.json",
        "REG_A_QB2X1_N1_solver_receipt.json": ROOT / "analysis" / "receipts" / "REG_A_QB2X1_N1.json",
    }
    saved = {}
    for name, source in sources.items():
        if not source.is_file():
            raise RuntimeError(f"cannot resume; prior attempt artifact missing: {source}")
        target = attempt_dir / name
        target.write_bytes(source.read_bytes())
        saved[name] = {"path": repo_rel(target), "sha256": sha256(target)}
    write_exclusive_json(attempt_dir / "archive_manifest.json", {
        "schema": "bvm-qb-repeatability-prior-platform-attempt-archive-v1",
        "attempt": "PLATFORM_ATTEMPT1", "files": saved,
        "purpose": "preserve the failed A analysis attempt before replacing root execution pointers",
        "scientific_interpretation_performed": False,
    })
    return saved


def recover_existing_a(case: dict, gate: dict, execution: dict) -> int:
    case_id = case["case_id"]
    original_receipt = ROOT / "analysis" / "receipts" / f"{case_id}.json"
    original_receipt_sha = sha256(original_receipt)
    command = [sys.executable, str(ROOT / "scripts" / "run_case.py"), "--analyze-only", case_id]
    print(f"\n=== {case_id}: analysis-only recovery of existing raw; no solver ===", flush=True)
    completed = subprocess.run(command, cwd=ROOT.parents[2], check=False)
    if completed.returncode != 0:
        execution["status"] = "STOPPED_ON_ANALYSIS_RECOVERY_FAILURE"
        write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
        print("Analysis recovery failed; the preserved raw was not rerun and no later case was started.", file=sys.stderr)
        return completed.returncode or 2
    run_dir = ROOT / "runs" / case_id
    metadata_path = run_dir / "metadata.json"
    result_path = run_dir / "result.json"
    metadata, result = read_json(metadata_path), read_json(result_path)
    if result.get("artifact_status") != "VALID" or result.get("raw_sha256") != metadata.get("raw", {}).get("sha256"):
        execution["status"] = "STOPPED_ON_ANALYSIS_RECOVERY_QA"
        write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
        print("Reanalyzed raw did not pass artifact QA; no solver retry or later case.", file=sys.stderr)
        return 2
    recovery_path = ROOT / "analysis" / "receipts" / f"{case_id}_reanalysis.json"
    recovery_receipt = {
        "schema": "bvm-qb-repeatability-analysis-recovery-receipt-v1",
        "case_id": case_id, "action": "REANALYZED_EXISTING_RAW_NO_SOLVE",
        "preflight_head": gate["git"]["head"],
        "preflight_qa_sha256": execution["preflight_qa_sha256"],
        "runner_command": command, "runner_exit_code": completed.returncode,
        "run_dir": repo_rel(run_dir), "physical_solve_count": 1,
        "new_physical_solve_count": 0, "analysis_status": result.get("analysis_status"),
        "plot_status": result.get("plot_status"), "artifact_status": result.get("artifact_status"),
        "raw_sha256": result["raw_sha256"],
        "solver": metadata.get("solver"), "parameters": metadata.get("parameters"),
        "supersedes_analysis_failure_receipt_path": repo_rel(original_receipt),
        "supersedes_analysis_failure_receipt_sha256": original_receipt_sha,
        "artifact_sha256": artifact_hashes(run_dir),
        "run_tree_file_sha256": run_tree_hashes(run_dir),
        "scientific_interpretation_performed": False,
    }
    write_exclusive_json(recovery_path, recovery_receipt)
    execution["runs"].append({
        "case_id": case_id, "action": "REANALYZED_EXISTING_RAW",
        "runner_command": command, "runner_exit_code": completed.returncode,
        "receipt_path": repo_rel(original_receipt), "receipt_sha256": original_receipt_sha,
        "analysis_recovery_receipt_path": repo_rel(recovery_path),
        "analysis_recovery_receipt_sha256": sha256(recovery_path),
        "physical_solve_count": 1, "new_physical_solve_count": 0,
        "raw_sha256": result["raw_sha256"], "status": "COMPLETE_EXISTING_SOLVE",
    })
    execution["completed_solve_count"] = 1
    execution["physical_solve_count"] = 1
    execution["new_physical_solve_count"] = 0
    write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
    return 0


def run_physical_case(case: dict, gate: dict, execution: dict) -> int:
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
    hashes = artifact_hashes(run_dir)
    receipt = {"schema": "bvm-qb-repeatability-independent-run-receipt-v1",
               "case_id": case["case_id"], "action": "NEW_PHYSICAL_SOLVE", "purpose": case["purpose"],
               "created_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
               "preflight_head": gate["git"]["head"],
               "preflight_qa_sha256": execution["preflight_qa_sha256"],
               "runner_command": command, "runner_exit_code": completed.returncode,
               "run_dir": str(run_dir.relative_to(ROOT.parents[2])),
               "execution_status": metadata.get("execution_status", "RUN_NOT_STARTED"),
               "artifact_status": result.get("artifact_status", "MISSING"),
               "physical_solve_count": int(metadata.get("physical_solve_count", 0)),
               "new_physical_solve_count": int(metadata.get("physical_solve_count", 0)),
               "parameters": metadata.get("parameters"), "solver": metadata.get("solver"),
               "artifact_sha256": hashes,
               "run_tree_file_sha256": run_tree_hashes(run_dir) if run_dir.is_dir() else {},
               "scientific_interpretation_performed": False, "automatic_follow_up": False}
    receipt_path = ROOT / "analysis" / "receipts" / f"{case['case_id']}.json"
    write_exclusive_json(receipt_path, receipt)
    execution["runs"].append({"case_id": case["case_id"], "action": "NEW_PHYSICAL_SOLVE",
                              "runner_command": command, "runner_exit_code": completed.returncode,
                              "receipt_path": repo_rel(receipt_path), "receipt_sha256": sha256(receipt_path),
                              "physical_solve_count": receipt["physical_solve_count"],
                              "new_physical_solve_count": receipt["new_physical_solve_count"],
                              "raw_sha256": hashes["raw"],
                              "status": "COMPLETE" if completed.returncode == 0 else "STOPPED_ON_FAILURE"})
    execution["completed_solve_count"] += 1
    execution["physical_solve_count"] += receipt["physical_solve_count"]
    execution["new_physical_solve_count"] += receipt["new_physical_solve_count"]
    if completed.returncode != 0:
        execution["status"] = "STOPPED_ON_FAILURE"
        write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
        print("Stopped at first failed case; no retry and no later case was run.", file=sys.stderr)
        return completed.returncode or 2
    write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
    return 0
def main() -> int:
    parser = argparse.ArgumentParser(description="Execute the exact five-case A–E matrix once")
    parser.add_argument("--dry-run", action="store_true", help="show exact cases without creating runs or solving")
    parser.add_argument("--resume", action="store_true",
                        help="preserve and reanalyze only the registered A raw, then execute B–E once")
    args = parser.parse_args()
    gate = build_gate(require_clean=not args.dry_run, resume_existing_a=args.resume)
    if args.dry_run:
        print(json.dumps({"preflight_status": gate["status"], "authorized_solve_count": gate["authorized_solve_count"],
                          "resume_existing_a": args.resume,
                          "existing_physical_solve_count": gate.get("existing_physical_solve_count", 0),
                          "new_physical_solve_count": gate.get("new_physical_solve_count", 0),
                          "cases": [{"case_id": item["case_id"], "action": item.get("action"),
                                     "parameters": item["parameters"],
                                     "read_schedule": item["schedule"], "stop_ps": item["stop_ps"]}
                                    for item in gate["cases"]], "no_solve_executed": True},
                         ensure_ascii=False, indent=2))
        return 0 if gate["status"] == "PASS" else 2
    if gate["status"] != "PASS":
        # Preserve the original stopped-at-A preflight if recovery validation fails.
        prior_execution_exists = (ROOT / "analysis" / "REGRESSION_EXECUTION.json").exists()
        prior_receipts_exist = ((ROOT / "analysis" / "receipts").is_dir() and
                                any((ROOT / "analysis" / "receipts").iterdir()))
        if not args.resume and not prior_execution_exists and not prior_receipts_exist:
            write_json(ROOT / "analysis" / "PREFLIGHT_QA.json", gate)
        print(json.dumps(gate, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    receipts_dir = ROOT / "analysis" / "receipts"
    execution_path = ROOT / "analysis" / "REGRESSION_EXECUTION.json"
    matrix = read_json(REGRESSION_MATRIX)
    archived = None
    if args.resume:
        # build_gate has validated the original stopped attempt and clean HEAD.
        # Archive before replacing either root ledger; creation is exclusive.
        archived = archive_previous_attempt()
    elif execution_path.exists() or (receipts_dir.exists() and any(receipts_dir.iterdir())):
        raise RuntimeError("registered regression execution/receipt evidence already exists; refusing restart/overwrite")

    write_json(ROOT / "analysis" / "PREFLIGHT_QA.json", gate)
    execution = {"schema": "bvm-qb-repeatability-regression-execution-v1",
                 "status": "IN_PROGRESS", "preflight_status": "PASS", "preflight_head": gate["git"]["head"],
                 "preflight_qa_sha256": sha256(ROOT / "analysis" / "PREFLIGHT_QA.json"),
                 "authorized_solve_count": int(matrix["authorized_solve_count"]),
                 "completed_solve_count": 0, "physical_solve_count": 0,
                 "new_physical_solve_count": 0,
                 "existing_physical_solve_count": int(gate.get("existing_physical_solve_count", 0)),
                 "automatic_retry": False, "scientific_interpretation_performed": False,
                 "prior_attempt_archive": archived, "runs": []}
    write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
    if args.resume:
        recovery_status = recover_existing_a(matrix[0], gate, execution)
        if recovery_status != 0:
            return recovery_status
        cases_to_run = matrix[1:]
    else:
        cases_to_run = matrix
    for case in cases_to_run:
        case_status = run_physical_case(case, gate, execution)
        if case_status != 0:
            return case_status
    execution["status"] = "ALL_REGISTERED_RUNS_COMPLETE"
    write_json(ROOT / "analysis" / "REGRESSION_EXECUTION.json", execution)
    final = subprocess.run([sys.executable, str(ROOT / "scripts" / "finalize.py")],
                           cwd=ROOT.parents[2], check=False)
    return final.returncode


if __name__ == "__main__":
    raise SystemExit(main())
