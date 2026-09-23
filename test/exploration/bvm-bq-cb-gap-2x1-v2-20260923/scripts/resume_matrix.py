#!/usr/bin/env python3
"""Resume only the remaining registered cases after same-raw header-format repair."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import analyze_run
import independent_verify
import run_matrix
from common import (MATRIX, REPO, ROOT, SOLVER, cases, current_head,
                    git_status, read_json, run_dir, sha256, solver_identity,
                    write_json)

SOURCE_LOCK = ROOT / "analysis" / "SOURCE_LOCK.json"
PREFLIGHT_QA = ROOT / "analysis" / "PREFLIGHT_QA.json"
EXECUTION = ROOT / "analysis" / "EXECUTION.json"
TOOL_REPAIR = ROOT / "analysis" / "TOOL_REPAIR.json"
TOOL_REPAIR_002 = ROOT / "analysis" / "TOOL_REPAIR_002.json"
REPAIR_ATTEMPT = ROOT / "analysis" / "REPAIR_ATTEMPT_001.json"
REPAIR_ATTEMPT_002 = ROOT / "analysis" / "REPAIR_ATTEMPT_002.json"
RESUME_PREFLIGHT = ROOT / "analysis" / "CONTINUATION_PREFLIGHT_QA.json"
TOOL_ROLES = {
    "SCRIPT_ANALYZE_RUN": "test/exploration/bvm-bq-cb-gap-2x1-v2-20260923/scripts/analyze_run.py",
    "SCRIPT_INDEPENDENT_VERIFY": "test/exploration/bvm-bq-cb-gap-2x1-v2-20260923/scripts/independent_verify.py",
    "SCRIPT_PLOT_RUN": "test/exploration/bvm-bq-cb-gap-2x1-v2-20260923/scripts/plot_run.py",
    "SCRIPT_TEST_PLATFORM": "test/exploration/bvm-bq-cb-gap-2x1-v2-20260923/scripts/test_platform.py",
}
EXPECTED_ALIASES = {
    "I(Lin|XBQ1)": "I(LIN|XBQ1)",
    "I(Lin|XBQ2)": "I(LIN|XBQ2)",
    "V(Lin|XBQ1)": "V(LIN|XBQ1)",
    "V(Lin|XBQ2)": "V(LIN|XBQ2)",
}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def verify_original_closure(source_lock: dict[str, Any], repair: dict[str, Any]) -> None:
    if sha256(SOURCE_LOCK) != repair.get("original_source_lock_sha256"):
        raise RuntimeError("original preregistered source lock changed")
    updated = repair.get("updated_script_sha256", {})
    if set(updated) != set(TOOL_ROLES):
        raise RuntimeError("tool repair script-role set differs from the four registered analysis tools")
    for role, frozen in source_lock.get("source_hashes", {}).items():
        path = REPO / frozen.get("path", "")
        expected = updated[role] if role in updated else frozen.get("sha256")
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"unregistered source/tool change during continuation: {role}")
    for role, relative in TOOL_ROLES.items():
        if repo_path(relative) != source_lock["source_hashes"][role]["path"]:
            raise RuntimeError(f"tool repair path differs from frozen role: {role}")
        if repair["updated_script_sha256"][role] != sha256(REPO / relative):
            raise RuntimeError(f"tool repair script hash mismatch: {role}")
    if repair.get("resume_runner_sha256") != sha256(Path(__file__)):
        raise RuntimeError("resume runner changed after repair record")
    solver = solver_identity()
    if solver.get("sha256") != source_lock.get("solver", {}).get("sha256") or solver.get("version") != source_lock.get("solver", {}).get("version"):
        raise RuntimeError("solver identity differs from the frozen original matrix")


def repo_path(relative: str) -> str:
    return (REPO / relative).resolve().relative_to(REPO.resolve()).as_posix()


def load_n0_evidence(preflight: dict[str, Any], execution: dict[str, Any],
                     allow_same_raw_repair: bool = False,
                     expected_original_head: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    if preflight.get("status") != "PASS":
        raise RuntimeError("the original machine preflight did not pass")
    expected_head = expected_original_head or current_head()
    if preflight.get("head") != expected_head:
        raise RuntimeError("the original machine preflight HEAD differs from repair provenance")
    if not allow_same_raw_repair and preflight.get("head") != current_head():
        raise RuntimeError("the original machine preflight is not at current HEAD")
    if preflight.get("source_lock_sha256") != sha256(SOURCE_LOCK):
        raise RuntimeError("the original source lock does not match preflight QA")
    if execution.get("physical_solve_count_started") != 1 or len(execution.get("runs", [])) != 1:
        raise RuntimeError("only one registered physical solve may have started before this repair")
    record = execution["runs"][0]
    if record.get("run_id") != "N0_00" or record.get("returncode") != 0 or not record.get("raw_exists"):
        raise RuntimeError("the preserved N0_00 solver receipt is not a successful raw-producing solve")
    expected_status = "RAW_QA_PASS_AFTER_SAME_RAW_REANALYSIS" if allow_same_raw_repair else "RAW_QA_FAIL_STOP"
    if record.get("status") != expected_status:
        raise RuntimeError("N0_00 is not at the expected analysis-only stop state")
    directory = run_dir("N0_00")
    receipt = read_json(directory / "solve_receipt.json")
    raw = directory / "raw.csv"
    metadata = read_json(directory / "metadata.json")
    if not raw.is_file() or sha256(raw) != receipt.get("raw", {}).get("sha256"):
        raise RuntimeError("preserved N0_00 raw hash differs from its solver receipt")
    if sha256(raw) != metadata.get("raw", {}).get("sha256"):
        raise RuntimeError("preserved N0_00 raw hash differs from run metadata")
    if sha256(directory / "actual_deck.cir") != preflight["cases"][0]["rendered_deck_sha256"]:
        raise RuntimeError("N0_00 deck differs from its frozen preflight rendering")
    if sha256(directory / "stimulus.inc") != preflight["cases"][0]["stimulus_sha256"]:
        raise RuntimeError("N0_00 stimulus differs from its frozen preflight rendering")
    raw_qa = read_json(directory / "analysis" / "raw_qa.json")
    analysis_qa = read_json(directory / "analysis" / "analysis_qa.json")
    independent = read_json(directory / "analysis" / "independent_check.json")
    if raw_qa.get("status") != "PASS" or analysis_qa.get("status") != "PASS" or independent.get("status") != "PASS":
        raise RuntimeError("same-raw reanalysis/independent QA is not PASS")
    if raw_qa.get("raw_sha256_before") != sha256(raw) or raw_qa.get("raw_sha256_after") != sha256(raw):
        raise RuntimeError("same-raw reanalysis does not prove immutable raw identity")
    if raw_qa.get("raw_header_aliases") != EXPECTED_ALIASES:
        raise RuntimeError(f"raw column aliases differ from the observed Lin/LIN-only format issue: {raw_qa.get('raw_header_aliases')}")
    return record, receipt


def prepare_repair() -> dict[str, Any]:
    if TOOL_REPAIR.exists() or REPAIR_ATTEMPT.exists() or RESUME_PREFLIGHT.exists():
        raise RuntimeError("repair artifacts already exist; refusing overwrite")
    preflight = read_json(PREFLIGHT_QA)
    execution = read_json(EXECUTION)
    source_lock = read_json(SOURCE_LOCK)
    record, solver_receipt = load_n0_evidence(preflight, execution)
    raw_qa = read_json(run_dir("N0_00") / "analysis" / "raw_qa.json")
    if raw_qa.get("raw_header_aliases") != EXPECTED_ALIASES:
        raise RuntimeError(f"raw aliases differ from the registered case-only formatting repair: {raw_qa.get('raw_header_aliases')}")
    updated_hashes = {role: sha256(REPO / relative) for role, relative in TOOL_ROLES.items()}
    for role, relative in TOOL_ROLES.items():
        if source_lock["source_hashes"][role]["path"] != repo_path(relative):
            raise RuntimeError(f"frozen tool path mismatch: {role}")
        if updated_hashes[role] == source_lock["source_hashes"][role]["sha256"]:
            raise RuntimeError(f"expected header-normalization repair is absent from {role}")
    for role, frozen in source_lock.get("source_hashes", {}).items():
        if role in updated_hashes:
            continue
        path = REPO / frozen["path"]
        if not path.is_file() or sha256(path) != frozen["sha256"]:
            raise RuntimeError(f"non-analysis frozen input changed during tool repair: {role}")
    repair = {
        "schema": "bvm-bq-cb-tool-repair-v1", "status": "SAME_RAW_QA_PASS_REMAINING_MATRIX_AUTHORIZED",
        "created_at": now(), "experiment_id": read_json(MATRIX)["experiment_id"],
        "original_preflight_sha256": sha256(PREFLIGHT_QA),
        "original_source_lock_sha256": sha256(SOURCE_LOCK),
        "original_parent_head": preflight["parent_head"],
        "current_head_before_repair_commit": current_head(),
        "prior_execution_count_started": 1, "remaining_registered_run_ids": ["N1_01", "N1_10", "N2_11"],
        "v2_authorized_solve_count": 4, "cumulative_solver_invocations_including_v1_incident": 5,
        "prior_solver_returncode": solver_receipt["returncode"],
        "prior_solver_stderr": solver_receipt.get("mechanical_qa_stderr", ""),
        "prior_analysis_error": solver_receipt.get("mechanical_qa_stderr", ""),
        "raw_sha256_before_reanalysis": sha256(run_dir("N0_00") / "raw.csv"),
        "raw_sha256_after_reanalysis": sha256(run_dir("N0_00") / "raw.csv"),
        "header_aliases": EXPECTED_ALIASES,
        "tool_repair": "Resolve JoSIM case-normalized raw header labels case-insensitively while preserving canonical probe labels; do not modify raw, deck, stimulus, topology, solver settings, or physics.",
        "same_raw_mechanical_qa": "PASS",
        "same_raw_independent_arithmetic_qa": "PASS",
        "raw_or_physical_rerun": False,
        "updated_script_sha256": updated_hashes,
        "resume_runner_sha256": sha256(Path(__file__)),
        "source_lock_physics_closure_unchanged": True,
        "scientific_interpretation_performed": False,
    }
    write_json(TOOL_REPAIR, repair)
    repair_attempt = {
        "schema": "bvm-bq-cb-analysis-repair-attempt-v1", "attempt_id": "REPAIR_001",
        "run_id": "N0_00", "created_at": repair["created_at"],
        "failure_kind": "ANALYZER_RAW_HEADER_CASE_ALIAS",
        "initial_solver_returncode": solver_receipt["returncode"],
        "initial_analyzer_returncode": solver_receipt.get("mechanical_qa_returncode"),
        "initial_analyzer_stderr": solver_receipt.get("mechanical_qa_stderr"),
        "raw_sha256": repair["raw_sha256_before_reanalysis"],
        "same_raw_mechanical_qa": "PASS", "same_raw_independent_arithmetic_qa": "PASS",
        "raw_unchanged": repair["raw_sha256_before_reanalysis"] == repair["raw_sha256_after_reanalysis"],
        "physical_solve_executed": False,
        "next_authorized_run_ids": repair["remaining_registered_run_ids"],
    }
    write_json(REPAIR_ATTEMPT, repair_attempt)
    context = {"schema": "bvm-bq-cb-run-tool-repair-context-v1",
               "repair_record_path": "analysis/TOOL_REPAIR.json",
               "repair_record_sha256": sha256(TOOL_REPAIR),
               "analysis_repair_attempt_path": "analysis/REPAIR_ATTEMPT_001.json",
               "analysis_repair_attempt_sha256": sha256(REPAIR_ATTEMPT),
               "raw_sha256": repair["raw_sha256_after_reanalysis"],
               "same_raw_reanalysis_only": True, "physical_solve_executed": False}
    write_json(run_dir("N0_00") / "analysis" / "TOOL_REPAIR_CONTEXT.json", context)
    execution["repair_history"] = [repair_attempt]
    execution["runs"][0]["status_history"] = ["RAW_QA_FAIL_STOP", "RAW_QA_PASS_AFTER_SAME_RAW_REANALYSIS"]
    execution["runs"][0]["status"] = "RAW_QA_PASS_AFTER_SAME_RAW_REANALYSIS"
    execution["runs"][0]["analysis_repair_attempt_path"] = REPAIR_ATTEMPT.relative_to(ROOT).as_posix()
    execution["runs"][0]["analysis_repair_attempt_sha256"] = sha256(REPAIR_ATTEMPT)
    execution["status"] = "N0_SAME_RAW_QA_REPAIRED_WAITING_REMAINING_CASES"
    execution["tool_repair_record_path"] = TOOL_REPAIR.relative_to(ROOT).as_posix()
    execution["tool_repair_record_sha256"] = sha256(TOOL_REPAIR)
    write_json(EXECUTION, execution)
    return repair


def prepare_continuation_lock() -> dict[str, Any]:
    """Append a final repair lock after the continuation runner itself is frozen."""
    context2 = run_dir("N0_00") / "analysis" / "TOOL_REPAIR_CONTEXT_002.json"
    if TOOL_REPAIR_002.exists() or REPAIR_ATTEMPT_002.exists() or context2.exists() or RESUME_PREFLIGHT.exists():
        raise RuntimeError("continuation repair lock already exists; refusing overwrite")
    original_repair = read_json(TOOL_REPAIR)
    if original_repair.get("status") != "SAME_RAW_QA_PASS_REMAINING_MATRIX_AUTHORIZED":
        raise RuntimeError("first same-raw repair record is not PASS")
    if original_repair.get("original_source_lock_sha256") != sha256(SOURCE_LOCK):
        raise RuntimeError("first repair record references a different source lock")
    preflight = read_json(PREFLIGHT_QA)
    execution = read_json(EXECUTION)
    source_lock = read_json(SOURCE_LOCK)
    load_n0_evidence(preflight, execution, allow_same_raw_repair=True,
                     expected_original_head=original_repair["current_head_before_repair_commit"])
    if current_head() != original_repair["current_head_before_repair_commit"]:
        raise RuntimeError("continuation repair code changed after the first repair record; preserving both records")
    if original_repair.get("original_source_lock_sha256") != sha256(SOURCE_LOCK):
        raise RuntimeError("original source-lock identity changed")
    updated_hashes = {role: sha256(REPO / relative) for role, relative in TOOL_ROLES.items()}
    for role, relative in TOOL_ROLES.items():
        if source_lock["source_hashes"][role]["path"] != repo_path(relative):
            raise RuntimeError(f"frozen tool path mismatch: {role}")
        if updated_hashes[role] == source_lock["source_hashes"][role]["sha256"]:
            raise RuntimeError(f"expected repaired tool hash missing: {role}")
    for role, frozen in source_lock.get("source_hashes", {}).items():
        if role in updated_hashes:
            continue
        path = REPO / frozen["path"]
        if not path.is_file() or sha256(path) != frozen["sha256"]:
            raise RuntimeError(f"non-analysis frozen input changed during continuation repair: {role}")
    repair = {
        "schema": "bvm-bq-cb-tool-repair-v2",
        "status": "FINAL_CONTINUATION_LOCKED",
        "created_at": now(),
        "experiment_id": read_json(MATRIX)["experiment_id"],
        "prior_repair_record_path": TOOL_REPAIR.relative_to(ROOT).as_posix(),
        "prior_repair_record_sha256": sha256(TOOL_REPAIR),
        "original_preflight_sha256": sha256(PREFLIGHT_QA),
        "original_source_lock_sha256": sha256(SOURCE_LOCK),
        "original_preflight_head": preflight["head"],
        "head_before_repair_checkpoint_commit": current_head(),
        "registered_physical_solve_count": 4,
        "already_completed_run_ids": ["N0_00"],
        "remaining_registered_run_ids": ["N1_01", "N1_10", "N2_11"],
        "v2_authorized_physical_solve_count_started": 1,
        "cumulative_solver_invocations_including_v1_incident": 5,
        "raw_sha256_before_and_after_same_raw_reanalysis": sha256(run_dir("N0_00") / "raw.csv"),
        "updated_script_sha256": updated_hashes,
        "resume_runner_sha256": sha256(Path(__file__)),
        "raw_or_physical_rerun": False,
        "physics_matrix_changed": False,
        "scientific_interpretation_performed": False,
    }
    write_json(TOOL_REPAIR_002, repair)
    repair_attempt = {"schema": "bvm-bq-cb-analysis-repair-attempt-v2",
                      "attempt_id": "REPAIR_002", "status": "PASS",
                      "prior_repair_record_sha256": repair["prior_repair_record_sha256"],
                      "resume_runner_sha256": repair["resume_runner_sha256"],
                      "script_hashes": updated_hashes,
                      "raw_sha256_before_after": repair["raw_sha256_before_and_after_same_raw_reanalysis"],
                      "physical_solve_executed": False,
                      "remaining_registered_run_ids": repair["remaining_registered_run_ids"]}
    write_json(REPAIR_ATTEMPT_002, repair_attempt)
    write_json(context2, {"schema": "bvm-bq-cb-run-tool-repair-context-v2",
                           "repair_record_path": TOOL_REPAIR_002.relative_to(ROOT).as_posix(),
                           "repair_record_sha256": sha256(TOOL_REPAIR_002),
                           "prior_repair_record_sha256": repair["prior_repair_record_sha256"],
                           "raw_sha256": repair["raw_sha256_before_and_after_same_raw_reanalysis"],
                           "same_raw_reanalysis_only": True, "physical_solve_executed": False})
    execution["repair_history"].append(repair_attempt)
    execution["tool_repair_record_v2_path"] = TOOL_REPAIR_002.relative_to(ROOT).as_posix()
    execution["tool_repair_record_v2_sha256"] = sha256(TOOL_REPAIR_002)
    execution["status"] = "N0_SAME_RAW_QA_REPAIRED_WAITING_REMAINING_CASES"
    write_json(EXECUTION, execution)
    return repair


def prepare_continuation(repair: dict[str, Any]) -> dict[str, Any]:
    if RESUME_PREFLIGHT.exists():
        raise RuntimeError("continuation preflight already exists; refusing overwrite")
    if git_status().strip():
        raise RuntimeError("commit the analysis-tool repair checkpoint before continuation physical runs")
    if current_head() == repair.get("head_before_repair_checkpoint_commit"):
        raise RuntimeError("analysis-tool repair checkpoint has not been committed")
    preflight = read_json(PREFLIGHT_QA)
    execution = read_json(EXECUTION)
    n0_record, _n0_receipt = load_n0_evidence(
        preflight, execution, allow_same_raw_repair=True,
        expected_original_head=repair["original_preflight_head"])
    if execution.get("status") != "N0_SAME_RAW_QA_REPAIRED_WAITING_REMAINING_CASES":
        raise RuntimeError("execution aggregate is not at the prepared repair continuation state")
    source_lock = read_json(SOURCE_LOCK)
    validate_repair_closure(source_lock, repair)
    remaining = [case["run_id"] for case in cases()[1:]]
    if remaining != repair["remaining_registered_run_ids"]:
        raise RuntimeError("remaining registered runs differ from tool repair record")
    if execution.get("physical_solve_count_started") != 1 or len(execution.get("runs", [])) != 1:
        raise RuntimeError("continuation expected exactly one already-started registered run")
    existing_dirs = sorted(path.name for path in (ROOT / "runs").iterdir() if path.is_dir())
    if existing_dirs != ["N0_00"]:
        raise RuntimeError(f"continuation refuses unexpected run directories: {existing_dirs}")
    qa = {"schema": "bvm-bq-cb-gap-continuation-preflight-v1", "status": "PASS",
          "created_at": now(), "head": current_head(), "original_preflight_head": preflight["head"],
          "original_source_lock_sha256": sha256(SOURCE_LOCK),
          "tool_repair_sha256": sha256(TOOL_REPAIR),
          "repaired_scripts": repair["updated_script_sha256"],
          "completed_registered_run": {"run_id": "N0_00", "raw_sha256": sha256(run_dir("N0_00") / "raw.csv"),
                                        "mechanical_qa": "PASS", "independent_qa": "PASS"},
          "remaining_authorized_run_ids": remaining,
          "remaining_physical_solve_count": 3,
          "cumulative_solver_invocations_including_v1_incident": 5,
          "physics_matrix_changed": False, "physical_solve_executed": False,
          "raw_or_deck_modified": False, "scientific_interpretation_performed": False}
    write_json(RESUME_PREFLIGHT, qa)
    execution["repair_commit_head"] = current_head()
    execution["continuation_preflight_path"] = RESUME_PREFLIGHT.relative_to(ROOT).as_posix()
    execution["continuation_preflight_sha256"] = sha256(RESUME_PREFLIGHT)
    write_json(EXECUTION, execution)
    return qa


def validate_repair_closure(source_lock: dict[str, Any], repair: dict[str, Any]) -> None:
    if sha256(SOURCE_LOCK) != repair.get("original_source_lock_sha256"):
        raise RuntimeError("original source lock changed")
    updated = repair.get("updated_script_sha256", {})
    if set(updated) != set(TOOL_ROLES):
        raise RuntimeError("tool repair script role set mismatch")
    for role, frozen in source_lock.get("source_hashes", {}).items():
        path = REPO / frozen["path"]
        expected = updated[role] if role in updated else frozen["sha256"]
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"source-lock repair closure mismatch at {role}")
    if repair.get("resume_runner_sha256") != sha256(Path(__file__)):
        raise RuntimeError("resume runner hash differs from repair record")
    solver = solver_identity()
    if solver.get("sha256") != source_lock["solver"].get("sha256") or solver.get("version") != source_lock["solver"].get("version"):
        raise RuntimeError("solver binary/version changed since the original preflight")


def execute_remaining() -> None:
    repair = read_json(TOOL_REPAIR_002)
    resume_qa = prepare_continuation(repair)
    source_lock = read_json(SOURCE_LOCK)
    execution = read_json(EXECUTION)
    preflight = read_json(PREFLIGHT_QA)
    resumed_preflight = dict(preflight)
    resumed_preflight["head"] = resume_qa["head"]

    # The circuit, matrix, solver, original source lock, and source snapshots are still
    # frozen. Only the case-normalized analysis/output-label adapters listed in TOOL_REPAIR changed.
    run_matrix.verify_live_source_lock = lambda lock: validate_repair_closure(lock, repair)
    for item in cases()[1:]:
        run_matrix.run_one(item, resumed_preflight, source_lock, execution)
        run_id = item["run_id"]
        context = {"schema": "bvm-bq-cb-gap-run-tool-repair-context-v2",
                   "repair_record_path": TOOL_REPAIR_002.relative_to(ROOT).as_posix(),
                   "repair_record_sha256": sha256(TOOL_REPAIR_002),
                   "raw_sha256": sha256(run_dir(run_id) / "raw.csv"),
                   "registered_probe_header_aliases": EXPECTED_ALIASES,
                   "physics_changed": False, "raw_modified": False,
                   "scientific_interpretation_performed": False}
        context_path = run_dir(run_id) / "analysis" / "TOOL_REPAIR_CONTEXT.json"
        write_json(context_path, context)
        execution["runs"][-1]["tool_repair_context_path"] = context_path.relative_to(ROOT).as_posix()
        execution["runs"][-1]["tool_repair_context_sha256"] = sha256(context_path)
        write_json(EXECUTION, execution)
    expected_ids = [case["run_id"] for case in cases()]
    actual_ids = [record["run_id"] for record in execution["runs"]]
    if actual_ids != expected_ids or execution["physical_solve_count_started"] != 4:
        raise RuntimeError(f"continuation did not complete exactly the registered matrix: {actual_ids}")
    execution["status"] = "ALL_FOUR_SOLVES_RAW_AND_INDEPENDENT_QA_PASS"
    execution["completed_at"] = now()
    execution["remaining_matrix_resume"] = {"preflight_path": RESUME_PREFLIGHT.relative_to(ROOT).as_posix(),
                                             "preflight_sha256": sha256(RESUME_PREFLIGHT),
                                             "no_physical_retry": True,
                                             "physical_solve_count_started": execution["physical_solve_count_started"]}
    write_json(EXECUTION, execution)
    print(json.dumps({"status": execution["status"],
                      "v2_physical_solve_count": execution["physical_solve_count_started"],
                      "runs": [item["run_id"] for item in execution["runs"]],
                      "prior_v1_incident_excluded": True}, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Repair N0 analysis on the same raw, then run only remaining registered v2 cases")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true", help="record tool repair after same-raw reanalysis; no physical solve")
    mode.add_argument("--prepare-continuation-lock", action="store_true", help="append a final tool-repair hash lock; no physical solve")
    mode.add_argument("--execute-remaining", action="store_true", help="after committed repair, execute only N1_01, N1_10, N2_11")
    args = parser.parse_args()
    if args.prepare_only:
        repair = prepare_repair()
        print(json.dumps({"status": repair["status"], "raw_reanalysis_only": True,
                          "physical_solve_executed": False,
                          "remaining_authorized_run_ids": repair["remaining_registered_run_ids"],
                          "tool_repair_sha256": sha256(TOOL_REPAIR)}, ensure_ascii=False, indent=2))
    elif args.prepare_continuation_lock:
        repair = prepare_continuation_lock()
        print(json.dumps({"status": repair["status"], "physical_solve_executed": False,
                          "remaining_registered_run_ids": repair["remaining_registered_run_ids"],
                          "tool_repair_sha256": sha256(TOOL_REPAIR_002)}, ensure_ascii=False, indent=2))
    else:
        execute_remaining()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
